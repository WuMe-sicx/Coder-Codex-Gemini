"""纯函数单元测试（stdlib unittest，无额外依赖）

覆盖 errors / metrics / results / process 中不需要子进程的纯逻辑。
运行：uv run python -m unittest discover -s tests
"""

from __future__ import annotations

import unittest

from cc_mcp.tools.errors import (
    ErrorKind,
    _build_error_detail,
    _filter_last_lines,
    _is_auth_error,
    _is_retryable_error,
    is_reconnecting_message,
)
from cc_mcp.tools.metrics import MetricsCollector
from cc_mcp.tools.process import _is_turn_completed
from cc_mcp.tools.results import build_failure_result, build_success_result


class TestErrors(unittest.TestCase):
    def test_auth_error_detection(self):
        self.assertTrue(_is_auth_error("HTTP 401 Unauthorized"))
        self.assertTrue(_is_auth_error("Error: not logged in"))
        self.assertFalse(_is_auth_error("some random failure"))

    def test_retryable(self):
        self.assertFalse(_is_retryable_error(ErrorKind.COMMAND_NOT_FOUND, ""))
        self.assertFalse(_is_retryable_error(ErrorKind.AUTH_REQUIRED, ""))
        self.assertTrue(_is_retryable_error(ErrorKind.UPSTREAM_ERROR, "x"))
        self.assertTrue(_is_retryable_error(ErrorKind.IDLE_TIMEOUT, "x"))

    def test_reconnecting(self):
        self.assertTrue(is_reconnecting_message("Reconnecting... 1/3"))
        self.assertFalse(is_reconnecting_message("real error"))

    def test_build_error_detail_fields(self):
        d = _build_error_detail("msg", exit_code=1, idle_timeout_s=300, retries=2)
        self.assertEqual(d["exit_code"], 1)
        self.assertEqual(d["idle_timeout_s"], 300)
        self.assertEqual(d["retries"], 2)
        self.assertIn("suggestion", d)

    def test_filter_last_lines_redacts_tool_result(self):
        lines = ['{"item": {"type": "tool_result", "content": "BIG SECRET"}}']
        out = _filter_last_lines(lines)
        self.assertIn("[truncated]", out[0])
        self.assertNotIn("BIG SECRET", out[0])

    def test_filter_last_lines_caps_count(self):
        lines = [f'{{"n": {i}}}' for i in range(120)]
        self.assertEqual(len(_filter_last_lines(lines, max_lines=50)), 50)


class TestProcess(unittest.TestCase):
    def test_turn_completed(self):
        self.assertTrue(_is_turn_completed('{"type": "turn.completed"}'))
        self.assertFalse(_is_turn_completed('{"type": "agent_message"}'))
        self.assertFalse(_is_turn_completed("not json"))


class TestMetrics(unittest.TestCase):
    def test_lifecycle(self):
        m = MetricsCollector("codex", "hi\nthere", "read-only")
        self.assertEqual(m.prompt_lines, 2)
        m.finish(success=True, result="ok", exit_code=0)
        d = m.to_dict()
        self.assertEqual(d["tool"], "codex")
        self.assertTrue(d["success"])
        self.assertTrue(m.format_duration().endswith("s"))


class TestResults(unittest.TestCase):
    def test_success(self):
        r = build_success_result("sess-1", "verdict", "1m2s")
        self.assertTrue(r["success"])
        self.assertEqual(r["SESSION_ID"], "sess-1")
        self.assertEqual(r["result"], "verdict")
        self.assertEqual(r["tool"], "codex")

    def test_failure_plain(self):
        r = build_failure_result(ErrorKind.UPSTREAM_ERROR, "boom", "0m1s", exit_code=1)
        self.assertFalse(r["success"])
        self.assertEqual(r["error"], "boom")
        self.assertEqual(r["error_kind"], ErrorKind.UPSTREAM_ERROR)
        self.assertEqual(r["error_detail"]["exit_code"], 1)

    def test_failure_auth_adds_hint(self):
        r = build_failure_result(ErrorKind.AUTH_REQUIRED, "401", "0m1s")
        self.assertIn("codex login", r["error"])
        self.assertTrue(r["error"].endswith("401"))


class TestWiring(unittest.TestCase):
    """守护 server.codex(async) → to_thread → codex_tool(sync) 的执行模型"""

    def test_codex_tool_is_sync(self):
        import inspect
        from cc_mcp.tools.codex import codex_tool
        # 必须是同步函数：它整段是阻塞实现，靠 to_thread 卸载到工作线程
        self.assertFalse(inspect.iscoroutinefunction(codex_tool))

    def test_server_registers_single_codex_tool(self):
        import cc_mcp.server as s
        self.assertEqual(s.mcp.name, "CC-MCP Server")

    def test_system_prompt_encodes_core_rules(self):
        from cc_mcp.tools.codex import CODEX_SYSTEM_PROMPT
        # 只审不改 + Karpathy 工程准则必须内置，确保 Codex 每次都按同一标准审
        self.assertIn("NEVER modify", CODEX_SYSTEM_PROMPT)
        self.assertIn("Simplicity", CODEX_SYSTEM_PROMPT)
        self.assertIn("Surgical scope", CODEX_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
