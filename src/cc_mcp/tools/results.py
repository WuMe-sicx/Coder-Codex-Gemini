"""Codex 工具返回值构建

把成功/失败的结构化返回字典构建逻辑抽离为纯函数，便于单测。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cc_mcp.tools.errors import ErrorKind, _build_error_detail

_AUTH_HINT = (
    "请先登录 Codex CLI。运行以下命令完成认证：\n"
    "  codex login\n"
    "\n"
    "或使用 API Key 认证：\n"
    "  printenv OPENAI_API_KEY | codex login --with-api-key\n"
    "\n"
)


def build_success_result(
    thread_id: Optional[str],
    agent_messages: str,
    duration: str,
) -> Dict[str, Any]:
    """构建成功返回字典"""
    return {
        "success": True,
        "tool": "codex",
        "SESSION_ID": thread_id,
        "result": agent_messages,
        "duration": duration,
    }


def build_failure_result(
    error_kind: Optional[str],
    err_message: str,
    duration: str,
    exit_code: Optional[int] = None,
    json_decode_errors: int = 0,
    all_last_lines: Optional[List[str]] = None,
    idle_timeout_s: Optional[int] = None,
    max_duration_s: Optional[int] = None,
    retries: int = 0,
) -> Dict[str, Any]:
    """构建失败返回字典（认证错误时附登录提示）"""
    final_error = err_message
    if error_kind == ErrorKind.AUTH_REQUIRED:
        final_error = _AUTH_HINT + err_message

    return {
        "success": False,
        "tool": "codex",
        "error": final_error,
        "error_kind": error_kind,
        "error_detail": _build_error_detail(
            message=err_message.split('\n')[0] if err_message else "未知错误",
            exit_code=exit_code,
            last_lines=all_last_lines,
            json_decode_errors=json_decode_errors,
            idle_timeout_s=idle_timeout_s,
            max_duration_s=max_duration_s,
            retries=retries,
        ),
        "duration": duration,
    }
