"""错误类型、结构化错误详情与可重试判断"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, Optional


# ============================================================================
# 错误类型定义
# ============================================================================

class CommandNotFoundError(Exception):
    """命令不存在错误"""
    pass


class CommandTimeoutError(Exception):
    """命令执行超时错误"""
    def __init__(self, message: str, is_idle: bool = False):
        super().__init__(message)
        self.is_idle = is_idle  # 标记是否为空闲超时


# ============================================================================
# 错误类型枚举
# ============================================================================

class ErrorKind:
    """结构化错误类型枚举"""
    TIMEOUT = "timeout"  # 总时长超时
    IDLE_TIMEOUT = "idle_timeout"  # 空闲超时（无输出）
    COMMAND_NOT_FOUND = "command_not_found"
    UPSTREAM_ERROR = "upstream_error"
    AUTH_REQUIRED = "auth_required"  # 需要登录认证
    JSON_DECODE = "json_decode"
    PROTOCOL_MISSING_SESSION = "protocol_missing_session"
    EMPTY_RESULT = "empty_result"
    SUBPROCESS_ERROR = "subprocess_error"
    UNEXPECTED_EXCEPTION = "unexpected_exception"


# ============================================================================
# 错误详情构建
# ============================================================================

def _filter_last_lines(lines: list[str], max_lines: int = 50) -> list[str]:
    """过滤 last_lines，脱敏 tool_result 中的大内容

    Codex 的 JSONL 格式：tool_result 在 item.type 中。
    这里只脱敏 tool_result 的 content 字段，保留消息结构和所有其他上下文。
    """
    filtered = []
    for line in lines:
        try:
            data = json.loads(line)
            item = data.get("item", {})

            # 脱敏 tool_result 内容
            if item.get("type") == "tool_result":
                data = copy.deepcopy(data)
                if "content" in data["item"]:
                    data["item"]["content"] = "[truncated]"
                filtered.append(json.dumps(data, ensure_ascii=False))
                continue

            # 其他消息类型正常保留
            filtered.append(line)
        except (json.JSONDecodeError, TypeError, AttributeError):
            # 非 JSON 行正常保留
            filtered.append(line)

    return filtered[-max_lines:]


def _build_error_detail(
    message: str,
    exit_code: Optional[int] = None,
    last_lines: Optional[list[str]] = None,
    json_decode_errors: int = 0,
    idle_timeout_s: Optional[int] = None,
    max_duration_s: Optional[int] = None,
    retries: int = 0,
) -> Dict[str, Any]:
    """构建结构化错误详情"""
    detail: Dict[str, Any] = {"message": message}
    if exit_code is not None:
        detail["exit_code"] = exit_code
    if last_lines:
        detail["last_lines"] = _filter_last_lines(last_lines, max_lines=50)
    if json_decode_errors > 0:
        detail["json_decode_errors"] = json_decode_errors
    if idle_timeout_s is not None:
        detail["idle_timeout_s"] = idle_timeout_s
        detail["suggestion"] = (
            "任务空闲超时（无输出）。建议：1) 增加 timeout 参数 "
            "2) 检查任务是否卡住 3) 拆分为更小的子任务"
        )
    if max_duration_s is not None:
        detail["max_duration_s"] = max_duration_s
        detail["suggestion"] = (
            "任务总时长超时。建议：1) 增加 max_duration 参数 "
            "2) 拆分为更小的子任务 3) 检查是否存在死循环"
        )
    if retries > 0:
        detail["retries"] = retries
    return detail


# ============================================================================
# 可重试错误判断
# ============================================================================

def _is_auth_error(text: str) -> bool:
    """检测是否为认证错误

    检测以下特征字符串（不区分大小写）：
    - 401
    - unauthorized
    - authentication failed
    - token refresh failed
    - login required
    - not logged in
    - invalid_grant
    - credentials
    """
    text_lower = text.lower()
    auth_keywords = [
        "401",
        "unauthorized",
        "authentication failed",
        "token refresh failed",
        "login required",
        "not logged in",
        "invalid_grant",
        "credentials",
    ]
    return any(keyword in text_lower for keyword in auth_keywords)


def _is_retryable_error(error_kind: Optional[str], err_message: str) -> bool:
    """判断错误是否可以重试

    Codex 是只读操作，大部分错误都可以安全重试。
    排除：命令不存在（需要用户干预）、认证错误（需要用户登录）
    """
    if error_kind == ErrorKind.COMMAND_NOT_FOUND:
        return False
    if error_kind == ErrorKind.AUTH_REQUIRED:
        return False
    # 其他错误都可以重试
    return True


def is_reconnecting_message(error_msg: str) -> bool:
    """判断是否为 Codex 的临时重连提示（非致命错误）"""
    return bool(re.match(r'^Reconnecting\.\.\.\s+\d+/\d+$', error_msg))
