"""Codex 工具实现

调用 Codex 进行独立代码审查（只审不改）。
子进程执行/超时/清理见 process.py，错误与指标见 errors.py / metrics.py。
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import Field

from cc_mcp.config import build_codex_env
from cc_mcp.tools.errors import (
    CommandNotFoundError,
    CommandTimeoutError,
    ErrorKind,
    _build_error_detail,
    _is_auth_error,
    _is_retryable_error,
    is_reconnecting_message,
)
from cc_mcp.tools.metrics import MetricsCollector
from cc_mcp.tools.process import safe_codex_command
from cc_mcp.tools.results import build_failure_result, build_success_result


# ============================================================================
# Codex System Prompt
# ============================================================================

CODEX_SYSTEM_PROMPT = """You are the final independent reviewer. Review; NEVER modify code or files. You are the last gate — the author cannot self-approve, so do not rubber-stamp.

Read-only. Check each item, and for every finding give `problem / location / severity / suggested fix`:
  1. Correctness — does it implement the stated requirement; any logic flaws.
  2. Boundary conditions — null/empty, off-by-one, out-of-range, invalid input, concurrency races.
  3. Security — injection, broken authz/authn, secret leakage, unsafe dependencies.
  4. Test gaps — are critical paths and edges covered; are the assertions actually meaningful.
  5. Maintainability / performance — obvious problems only (optional).

Explicitly flag high-risk surfaces: data loss, auth/authz, payments, data writes, external interfaces, concurrency, migrations, and any irreversible or externally-visible behavior. Skip style nits unless they hide a defect.

Scope: The diff is the unit of review; inspect surrounding code when behavior is unclear and report what you found.

Verdict — end with exactly one line:
  ✅ PASS — ship as-is (no issues; state this explicitly = "通过").
  ⚠️ OPTIMIZE — ships; list concrete improvements.
  ❌ CHANGE — must fix; list blockers as `file:line · severity · root cause · fix`.

Output: Provide evidence and context for every finding. Length matches the risk surface — thorough where it matters, silent where it doesn't. No diff restatement, no filler, no emojis."""


# ============================================================================
# 主工具函数
# ============================================================================

async def codex_tool(
    PROMPT: Annotated[str, "审核任务描述"],
    cd: Annotated[Path, "工作目录"],
    sandbox: Annotated[
        Literal["read-only", "workspace-write", "danger-full-access"],
        Field(description="沙箱策略，默认只读"),
    ] = "read-only",
    SESSION_ID: Annotated[str, "会话 ID，用于多轮对话"] = "",
    skip_git_repo_check: Annotated[
        bool,
        "允许在非 Git 仓库中运行",
    ] = True,
    return_all_messages: Annotated[bool, "是否返回完整消息"] = False,
    return_metrics: Annotated[bool, "是否在返回值中包含指标数据"] = False,
    image: Annotated[
        Optional[List[Path]],
        Field(description="附加图片文件路径列表"),
    ] = None,
    model: Annotated[
        str,
        Field(description="指定模型，默认使用 Codex 自己的配置"),
    ] = "",
    yolo: Annotated[
        bool,
        Field(description="无需审批运行所有命令（跳过沙箱）"),
    ] = False,
    profile: Annotated[
        str,
        "从 ~/.codex/config.toml 加载的配置文件名称",
    ] = "",
    timeout: Annotated[
        int,
        Field(description="空闲超时（秒），无输出超过此时间触发超时，默认 300 秒"),
    ] = 300,
    max_duration: Annotated[
        int,
        Field(description="总时长硬上限（秒），默认 1800 秒（30 分钟），0 表示无限制"),
    ] = 1800,
    max_retries: Annotated[int, "最大重试次数，默认 1（Codex 只读可安全重试）"] = 1,
    log_metrics: Annotated[bool, "是否将指标输出到 stderr"] = False,
) -> Dict[str, Any]:
    """执行 Codex 代码审核

    调用 Codex 进行独立代码审查。

    **角色定位**：最终独立审查者（只审不改）
    - 检查逻辑正确性、边界条件、安全风险、测试缺口、可维护性
    - 给出明确结论：✅ PASS 通过 / ⚠️ OPTIMIZE 建议优化 / ❌ CHANGE 需要修改

    **注意**：Codex 仅审核，严禁修改代码，默认 sandbox 为 read-only
    **重试策略**：Codex 默认允许 1 次重试（只读操作无副作用）
    """
    # 初始化指标收集器
    metrics = MetricsCollector(tool="codex", prompt=PROMPT, sandbox=sandbox)

    # 归一化可选参数
    image_list = image or []

    # 构建命令（shell=False 时不需要转义）
    cmd = ["codex", "exec", "--sandbox", sandbox, "--cd", str(cd), "--json"]

    if image_list:
        cmd.extend(["--image", ",".join(str(p) for p in image_list)])

    if model:
        cmd.extend(["--model", model])

    if profile:
        cmd.extend(["--profile", profile])

    if yolo:
        cmd.append("--yolo")

    if skip_git_repo_check:
        cmd.append("--skip-git-repo-check")

    if SESSION_ID:
        cmd.extend(["resume", str(SESSION_ID)])

    # PROMPT 通过 stdin 传递，不再作为命令行参数

    # 构建隔离的子进程环境，移除父进程 Claude Code 干扰变量
    codex_env = build_codex_env()

    # 注入系统提示词（Codex CLI 无原生 system prompt flag，通过 stdin prepend 注入）
    full_prompt = f"# System\n{CODEX_SYSTEM_PROMPT}\n\n# Task\n{PROMPT}"

    # 执行循环（支持重试）
    retries = 0
    last_error: Optional[Dict[str, Any]] = None
    all_last_lines: list[str] = []

    while retries <= max_retries:
        all_messages: list[Dict[str, Any]] = []
        agent_messages = ""
        had_error = False
        err_message = ""
        thread_id: Optional[str] = None
        exit_code: Optional[int] = None
        raw_output_lines = 0
        json_decode_errors = 0
        error_kind: Optional[str] = None
        last_lines: list[str] = []

        try:
            with safe_codex_command(cmd, timeout=timeout, max_duration=max_duration, prompt=full_prompt, env=codex_env, cwd=cd) as (gen, result_holder):
                for line in gen:
                    last_lines.append(line)
                    if len(last_lines) > 50:
                        last_lines.pop(0)

                    try:
                        line_dict = json.loads(line.strip())

                        # 收集消息（脱敏 tool_result 内容）
                        if return_all_messages:
                            safe_dict = copy.deepcopy(line_dict)
                            item = safe_dict.get("item", {})
                            # Codex 的 tool_result 在 item 中
                            if item.get("type") == "tool_result":
                                # 只保留 tool_use_id 和 type，脱敏 content
                                if "content" in item:
                                    item["content"] = "[truncated]"
                            all_messages.append(safe_dict)

                        item = line_dict.get("item", {})
                        item_type = item.get("type", "")

                        if item_type == "agent_message":
                            agent_messages += item.get("text", "")

                        if line_dict.get("thread_id") is not None:
                            thread_id = line_dict.get("thread_id")

                        # 错误处理：记录错误但不立即判断成功与否
                        # 注意：AUTH_REQUIRED 优先级最高，一旦设置不再被覆盖
                        if "fail" in line_dict.get("type", ""):
                            had_error = True
                            fail_msg = line_dict.get("error", {}).get("message", "")
                            err_message += "\n\n[codex error] " + fail_msg
                            # 检测是否为认证错误（优先级高于 UPSTREAM_ERROR）
                            if _is_auth_error(fail_msg):
                                error_kind = ErrorKind.AUTH_REQUIRED
                            elif error_kind != ErrorKind.AUTH_REQUIRED:
                                error_kind = ErrorKind.UPSTREAM_ERROR

                        if "error" in line_dict.get("type", ""):
                            error_msg = line_dict.get("message", "")

                            if not is_reconnecting_message(error_msg):
                                had_error = True
                                err_message += "\n\n[codex error] " + error_msg
                                # 检测是否为认证错误（优先级高于 UPSTREAM_ERROR）
                                if _is_auth_error(error_msg):
                                    error_kind = ErrorKind.AUTH_REQUIRED
                                elif error_kind != ErrorKind.AUTH_REQUIRED:
                                    error_kind = ErrorKind.UPSTREAM_ERROR

                    except json.JSONDecodeError:
                        # JSON 解析失败记录但不影响成功判定
                        json_decode_errors += 1
                        err_message += "\n\n[json decode error] " + line
                        continue

                    except Exception as error:
                        err_message += f"\n\n[unexpected error] {error}. Line: {line!r}"
                        had_error = True
                        error_kind = ErrorKind.UNEXPECTED_EXCEPTION
                        break

                # 从 result_holder 读取进程退出信息
                exit_code = result_holder["exit_code"]
                raw_output_lines = result_holder["raw_output_lines"]

        except CommandNotFoundError as e:
            metrics.finish(
                success=False,
                error_kind=ErrorKind.COMMAND_NOT_FOUND,
                retries=retries,
            )
            if log_metrics:
                metrics.log_to_stderr()

            result: Dict[str, Any] = {
                "success": False,
                "tool": "codex",
                "error": str(e),
                "error_kind": ErrorKind.COMMAND_NOT_FOUND,
                "error_detail": _build_error_detail(str(e)),
            }
            if return_metrics:
                result["metrics"] = metrics.to_dict()
            return result

        except CommandTimeoutError as e:
            # 根据异常属性区分空闲超时和总时长超时
            error_kind = ErrorKind.IDLE_TIMEOUT if e.is_idle else ErrorKind.TIMEOUT
            had_error = True
            err_message = str(e)
            success = False  # 明确设置为失败
            # 超时可以重试（Codex 只读）
            all_last_lines = last_lines.copy()
            last_error = {
                "error_kind": error_kind,
                "err_message": err_message,
                "exit_code": exit_code,
                "json_decode_errors": json_decode_errors,
                "raw_output_lines": raw_output_lines,
            }
            if retries < max_retries:
                retries += 1
                time.sleep(0.5 * (2 ** (retries - 1)))
                continue
            else:
                # 已达最大重试次数
                break

        # 综合判断成功与否
        success = True

        if had_error:
            success = False

        if thread_id is None:
            success = False
            if not error_kind:
                error_kind = ErrorKind.PROTOCOL_MISSING_SESSION
            err_message = "未能获取 SESSION_ID。\n\n" + err_message

        if not agent_messages:
            success = False
            if not error_kind:
                error_kind = ErrorKind.EMPTY_RESULT
            err_message = "未能获取 Codex 响应内容。可尝试设置 return_all_messages=True 获取详细信息。\n\n" + err_message

        # 检查退出码
        if exit_code is not None and exit_code != 0 and success:
            success = False
            if not error_kind:
                error_kind = ErrorKind.SUBPROCESS_ERROR
            err_message = f"进程退出码非零：{exit_code}\n\n" + err_message

        if success:
            # 成功，跳出重试循环
            break
        else:
            # 记录本轮失败信息
            all_last_lines = last_lines.copy()
            last_error = {
                "error_kind": error_kind,
                "err_message": err_message,
                "exit_code": exit_code,
                "json_decode_errors": json_decode_errors,
                "raw_output_lines": raw_output_lines,
            }
            # 检查是否可重试
            if _is_retryable_error(error_kind, err_message) and retries < max_retries:
                retries += 1
                # 指数退避
                time.sleep(0.5 * (2 ** (retries - 1)))
            else:
                # 不可重试或已达到最大重试次数
                break

    # 完成指标收集
    metrics.finish(
        success=success,
        error_kind=error_kind,
        result=agent_messages,
        exit_code=exit_code,
        raw_output_lines=raw_output_lines,
        json_decode_errors=json_decode_errors,
        retries=retries,
    )
    if log_metrics:
        metrics.log_to_stderr()

    # 构建返回结果
    if success:
        result = build_success_result(
            thread_id=thread_id,
            agent_messages=agent_messages,
            duration=metrics.format_duration(),
        )
    else:
        # 使用最后一次失败的错误信息
        if last_error:
            error_kind = last_error["error_kind"]
            err_message = last_error["err_message"]
            exit_code = last_error["exit_code"]
            json_decode_errors = last_error["json_decode_errors"]

        result = build_failure_result(
            error_kind=error_kind,
            err_message=err_message,
            duration=metrics.format_duration(),
            exit_code=exit_code,
            json_decode_errors=json_decode_errors,
            all_last_lines=all_last_lines,
            idle_timeout_s=timeout if error_kind == ErrorKind.IDLE_TIMEOUT else None,
            max_duration_s=max_duration if error_kind == ErrorKind.TIMEOUT else None,
            retries=retries,
        )

    if return_all_messages:
        result["all_messages"] = all_messages

    if return_metrics:
        result["metrics"] = metrics.to_dict()

    return result
