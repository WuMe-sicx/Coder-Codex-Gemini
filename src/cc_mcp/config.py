"""环境变量构建模块

本服务器只提供 Codex 代码审查工具，Codex 使用其自身 CLI 的认证与配置
（`codex login` / `OPENAI_API_KEY` / `~/.codex/config.toml`），因此无需任何
本地配置文件。这里唯一的职责是为子进程构建一份干净的环境变量，
移除父进程 Claude Code 注入的干扰变量，避免多实例运行时互相污染。
"""

from __future__ import annotations

import os

# 父进程 Claude Code 设置的干扰变量，必须从子进程环境中移除：
# CLAUDE_CODE_ENTRYPOINT 等会改变 CLI 行为；ANTHROPIC_* 是 Claude 侧凭证，
# 不应泄漏到使用 OpenAI 的 Codex 子进程。
_PARENT_CLAUDE_VARS = [
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING",
    "CLAUDE_AGENT_SDK_VERSION",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
]

# Anthropic 认证相关变量，避免泄漏到 Codex（使用 OpenAI API）
_ANTHROPIC_CREDENTIAL_VARS = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
]


def build_codex_env() -> dict[str, str]:
    """构建 Codex 调用所需的干净环境变量

    Codex 使用自身认证（codex login / OPENAI_API_KEY）和配置（~/.codex/config.toml），
    不需要注入任何密钥。这里只做减法：移除父进程 Claude Code 的干扰变量及
    Anthropic 凭证，防止多实例运行时环境变量互相污染或凭证错配。

    Returns:
        干净的环境变量字典，用于 subprocess.Popen(env=...)
    """
    env = os.environ.copy()

    for var in _PARENT_CLAUDE_VARS:
        env.pop(var, None)

    for var in _ANTHROPIC_CREDENTIAL_VARS:
        env.pop(var, None)

    return env
