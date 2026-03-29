"""配置加载模块

优先级：配置文件 > 环境变量
配置文件路径：~/.ccg-mcp/config.toml
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

# 示例模型名称，仅用于配置引导文本
_EXAMPLE_MODEL = "glm-4.7"


class ConfigError(Exception):
    """配置错误"""
    pass


def _read_windows_env_var(name: str) -> str:
    """从 Windows 注册表读取环境变量（绕过进程环境快照）

    Windows 上 os.environ 是进程启动时的快照，后续通过系统设置添加的
    环境变量不会自动刷新。此函数直接从注册表读取当前实际值。

    优先级：用户环境变量 > 系统环境变量

    Args:
        name: 环境变量名

    Returns:
        环境变量值，未找到或非 Windows 平台返回空字符串
    """
    if os.name != "nt":
        return ""

    try:
        import winreg

        # 先查用户级环境变量（HKCU\Environment）
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value:
                    return str(value)
        except (FileNotFoundError, OSError):
            pass

        # 再查系统级环境变量（HKLM\...\Environment）
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value:
                    return str(value)
        except (FileNotFoundError, OSError):
            pass
    except ImportError:
        pass

    return ""


def get_config_path() -> Path:
    """获取配置文件路径"""
    return Path.home() / ".ccg-mcp" / "config.toml"


def load_config() -> dict[str, Any]:
    """加载配置，优先级：配置文件 > 环境变量

    Returns:
        配置字典，包含 coder 和 codex 配置

    Raises:
        ConfigError: 未找到有效配置时抛出
    """
    config_path = get_config_path()

    # 优先读取配置文件
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"配置文件格式错误：{e}")

    # 兜底：从环境变量读取
    if os.environ.get("CODER_API_TOKEN"):
        return {
            "coder": {
                "api_token": os.environ["CODER_API_TOKEN"],
                "base_url": os.environ.get(
                    "CODER_BASE_URL",
                    "https://open.bigmodel.cn/api/anthropic"
                ),
                "model": os.environ.get("CODER_MODEL", ""),
            }
        }

    # 生成配置引导信息
    config_example = f'''# ~/.ccg-mcp/config.toml

[coder]
api_token = "your-api-token"  # 必填
base_url = "https://open.bigmodel.cn/api/anthropic"  # 示例：GLM API
model = "{_EXAMPLE_MODEL}"  # 示例，可替换为其他模型

# 可选：额外环境变量
[coder.env]
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
'''

    raise ConfigError(
        f"未找到 Coder 配置！\n\n"
        f"Coder 工具需要用户自行配置后端模型。\n"
        f"推荐使用 {_EXAMPLE_MODEL} 作为参考案例，也可选用其他支持 Claude Code API 的模型（如 Minimax、DeepSeek 等）。\n\n"
        f"请创建配置文件：{config_path}\n\n"
        f"配置文件示例：\n{config_example}\n"
        f"或设置环境变量 CODER_API_TOKEN"
    )


def build_coder_env(config: dict[str, Any]) -> dict[str, str]:
    """构建 Coder 调用所需的环境变量

    Args:
        config: 配置字典

    Returns:
        包含所有环境变量的字典
    """
    coder_config = config.get("coder", {})
    model = coder_config.get("model", "")

    env = os.environ.copy()

    # 清理父进程继承的干扰变量
    # CLAUDE_CODE_ENTRYPOINT=claude-vscode 会导致 -p 模式下 API Key 被拒绝
    # ANTHROPIC_MODEL/ANTHROPIC_SMALL_FAST_MODEL 会绕过别名映射，导致使用了错误的模型
    _parent_vars_to_remove = [
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING",
        "CLAUDE_AGENT_SDK_VERSION",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
    ]
    for var in _parent_vars_to_remove:
        env.pop(var, None)

    # API 认证：通过 ANTHROPIC_API_KEY（x-api-key 头）
    api_token = coder_config.get("api_token", "")
    env["ANTHROPIC_API_KEY"] = api_token
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["ANTHROPIC_BASE_URL"] = coder_config.get(
        "base_url",
        "https://open.bigmodel.cn/api/anthropic"
    )

    # 所有模型别名都映射到配置的模型
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
    env["CLAUDE_CODE_SUBAGENT_MODEL"] = model

    # 用户自定义的额外环境变量
    for key, value in coder_config.get("env", {}).items():
        env[key] = str(value)

    return env


def build_gemini_env(config: dict[str, Any]) -> dict[str, str]:
    """构建 Gemini 调用所需的环境变量

    从 config.toml 的 [gemini] 段读取 api_key，注入 GEMINI_API_KEY。
    如果未配置 [gemini] 段，返回当前环境的副本（保持向后兼容）。

    Args:
        config: 配置字典

    Returns:
        包含所有环境变量的字典
    """
    gemini_config = config.get("gemini", {})
    if not isinstance(gemini_config, dict):
        gemini_config = {}
    env = os.environ.copy()

    # 设置 GEMINI_API_KEY
    # 优先级：config.toml > os.environ > Windows 注册表
    api_key = gemini_config.get("api_key", "")
    if api_key:
        env["GEMINI_API_KEY"] = api_key
    elif not env.get("GEMINI_API_KEY"):
        # os.environ 中也没有，尝试从 Windows 注册表读取实际值
        # （解决 VSCode/Claude Code 进程环境快照过期的问题）
        registry_key = _read_windows_env_var("GEMINI_API_KEY")
        if registry_key:
            env["GEMINI_API_KEY"] = registry_key

    # 设置 GOOGLE_GEMINI_BASE_URL（如果配置了）
    base_url = gemini_config.get("base_url", "")
    if base_url:
        env["GOOGLE_GEMINI_BASE_URL"] = base_url

    # 用户自定义的额外环境变量
    for key, value in gemini_config.get("env", {}).items():
        env[key] = str(value)

    return env


def build_coder_settings_json(config: dict[str, Any]) -> str:
    """构建 --settings 参数的 JSON 字符串

    用于覆盖父进程 settings.json 中的 env 块，确保 Coder 使用正确的 API 配置和模型。
    Claude CLI 加载 settings.json 时会覆盖进程环境变量，因此必须通过 --settings
    参数以更高优先级注入正确的值（包括 API key、base URL 和模型配置）。

    Args:
        config: 配置字典

    Returns:
        JSON 字符串，传递给 claude CLI 的 --settings 参数
    """
    import json

    coder_config = config.get("coder", {})
    model = coder_config.get("model", "")
    api_token = coder_config.get("api_token", "")

    settings = {
        "env": {
            "ANTHROPIC_API_KEY": api_token,
            "ANTHROPIC_BASE_URL": coder_config.get(
                "base_url",
                "https://open.bigmodel.cn/api/anthropic"
            ),
            # 清空 AUTH_TOKEN 防止父进程的 token 干扰认证
            "ANTHROPIC_AUTH_TOKEN": "",
            # 设为空字符串强制 CLI 走默认模型路径，使其尊重 ANTHROPIC_DEFAULT_*_MODEL 别名
            "ANTHROPIC_MODEL": "",
            "ANTHROPIC_SMALL_FAST_MODEL": model,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
            "CLAUDE_CODE_SUBAGENT_MODEL": model,
        }
    }

    return json.dumps(settings, ensure_ascii=False)


def validate_config(config: dict[str, Any]) -> None:
    """验证配置有效性

    Args:
        config: 配置字典

    Raises:
        ConfigError: 配置无效时抛出
    """
    coder_config = config.get("coder", {})

    if not coder_config.get("api_token", "").strip():
        raise ConfigError("Coder 配置缺少 api_token")

    if not coder_config.get("base_url", "").strip():
        raise ConfigError("Coder 配置缺少 base_url")

    if not coder_config.get("model", "").strip():
        raise ConfigError("Coder 配置缺少 model（模型名称）")


# 全局配置缓存
_config_cache: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """获取配置（带缓存）

    首次调用时加载配置并验证，后续调用直接返回缓存

    Returns:
        配置字典
    """
    global _config_cache

    if _config_cache is None:
        _config_cache = load_config()
        validate_config(_config_cache)

    return _config_cache


def reset_config_cache() -> None:
    """重置配置缓存（主要用于测试）"""
    global _config_cache
    _config_cache = None
