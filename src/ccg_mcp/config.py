"""配置加载模块

优先级：配置文件 > 环境变量
配置文件路径：~/.ccg-mcp/config.toml
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

# 示例模型名称，仅用于配置引导文本
_EXAMPLE_MODEL = "glm-4.7"

# 父进程 Claude Code 设置的干扰变量，必须从子进程环境中移除
# CLAUDE_CODE_ENTRYPOINT=claude-vscode 会导致 -p 模式下 API Key 被拒绝
# ANTHROPIC_MODEL/ANTHROPIC_SMALL_FAST_MODEL 会绕过别名映射，导致使用了错误的模型
_PARENT_CLAUDE_VARS = [
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING",
    "CLAUDE_AGENT_SDK_VERSION",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL",
]


class ConfigError(Exception):
    """配置错误"""
    pass


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


# 1M 上下文模型后缀（Claude CLI 识别此后缀后会自动附带 anthropic-beta: context-1m-2025-08-07 header）
_CONTEXT_1M_SUFFIX = "[1m]"


def _resolve_coder_model(coder_config: dict[str, Any]) -> str:
    """解析最终要写入 ANTHROPIC_*_MODEL 的模型名

    支持两种启用 1M 上下文的方式，最终都会让模型名带上 `[1m]` 后缀，
    由 Claude CLI 自动注入 `anthropic-beta: context-1m-2025-08-07` header：

    1. 显式配置 `enable_1m_context = true`（若 model 未带 [1m]，自动补齐）
    2. 直接在 model 中使用 `[1m]` 后缀（保持原样）

    Raises:
        ConfigError: 去掉 [1m] 后模型名为空时抛出
    """
    model = coder_config.get("model", "")
    enable_1m = bool(coder_config.get("enable_1m_context", False))

    has_suffix = model.endswith(_CONTEXT_1M_SUFFIX)
    base = model[: -len(_CONTEXT_1M_SUFFIX)] if has_suffix else model

    if not base.strip():
        raise ConfigError("Coder 配置的 model 去除 [1m] 后为空，请填写有效模型名")

    # 启用 1M(显式 true 或 model 已带 [1m])时，统一让最终模型名带上 [1m] 后缀
    if enable_1m or has_suffix:
        return base + _CONTEXT_1M_SUFFIX
    return base


def build_coder_env(config: dict[str, Any]) -> dict[str, str]:
    """构建 Coder 调用所需的环境变量

    Args:
        config: 配置字典

    Returns:
        包含所有环境变量的字典
    """
    coder_config = config.get("coder", {})
    model = _resolve_coder_model(coder_config)

    env = os.environ.copy()

    # 清理父进程继承的干扰变量
    for var in _PARENT_CLAUDE_VARS:
        env.pop(var, None)

    # API 认证：通过 ANTHROPIC_API_KEY（x-api-key 头）
    api_token = coder_config.get("api_token", "")
    env["ANTHROPIC_API_KEY"] = api_token
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["ANTHROPIC_BASE_URL"] = coder_config.get(
        "base_url",
        "https://open.bigmodel.cn/api/anthropic"
    )

    # 所有模型别名都映射到配置的模型（若启用 1M，model 带 [1m] 后缀，CLI 会自动注入 beta header）
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
    env["CLAUDE_CODE_SUBAGENT_MODEL"] = model

    # 用户自定义的额外环境变量（会覆盖上面的默认值）
    for key, value in coder_config.get("env", {}).items():
        if value is None:
            continue
        env[key] = str(value)

    return env


def build_codex_env() -> dict[str, str]:
    """构建 Codex 调用所需的环境变量

    Codex 使用自身认证（codex login / OPENAI_API_KEY）和配置（~/.codex/config.toml），
    不需要注入 API 密钥。主要目的是移除父进程 Claude Code 的干扰变量，
    防止多实例运行时环境变量互相污染。

    Returns:
        干净的环境变量字典，用于 subprocess.Popen(env=...)
    """
    env = os.environ.copy()

    # 移除父进程 Claude Code 干扰变量
    for var in _PARENT_CLAUDE_VARS:
        env.pop(var, None)

    # 额外移除 Anthropic 认证变量，避免泄漏到 Codex（使用 OpenAI API）
    _anthropic_credential_vars = [
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
    ]
    for var in _anthropic_credential_vars:
        env.pop(var, None)

    return env


_GEMINI_ENV_KEYS = {"GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GEMINI_BASE_URL", "GEMINI_MODEL"}


def _gemini_env_candidates() -> list[Path]:
    """返回 ~/.gemini/.env 的候选路径列表（去重，保序）"""
    # 显式 override
    override = (os.environ.get("CCG_GEMINI_ENV_FILE") or "").strip()
    if override:
        return [Path(override).expanduser()]

    seen: set[str] = set()
    candidates: list[Path] = []

    def _add(base: str | None) -> None:
        if not base:
            return
        p = Path(base) / ".gemini" / ".env"
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    _add(os.environ.get("HOME"))
    _add(os.environ.get("USERPROFILE"))
    homedrive = os.environ.get("HOMEDRIVE", "")
    homepath = os.environ.get("HOMEPATH", "")
    if homedrive and homepath:
        _add(homedrive + homepath)
    try:
        _add(str(Path.home()))
    except Exception:
        pass

    return candidates


def _load_gemini_dotenv() -> dict[str, str]:
    """从候选路径读取 ~/.gemini/.env，返回第一个成功解析的结果。

    Gemini CLI 的原生配置位置，格式为 KEY=VALUE（支持 # 注释和引号）。
    主动读取并注入到子进程环境，确保不依赖父进程（VSCode）的环境快照。

    Returns:
        解析出的环境变量字典
    """
    result: dict[str, str] = {}
    errors: list[str] = []
    checked: list[str] = []

    for env_path in _gemini_env_candidates():
        checked.append(str(env_path))
        if not env_path.exists():
            continue
        try:
            content = env_path.read_text(encoding="utf-8-sig")  # utf-8-sig 自动去除 BOM
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 去掉 export 前缀
                if line.startswith("export "):
                    line = line[7:].lstrip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # 去除可选的引号包裹（引号内的 # 保留）
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                else:
                    # 无引号包裹时，去除行尾注释
                    hash_pos = value.find("#")
                    if hash_pos != -1:
                        value = value[:hash_pos].rstrip()
                if key:
                    result[key] = value
            if result.keys() & _GEMINI_ENV_KEYS:
                break  # 包含有效白名单键，使用此文件
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"{env_path}: {e.__class__.__name__}: {e}")

    if errors and not result:
        print(
            f"[ccg-mcp] Gemini env load failed. checked={checked}; errors={errors}",
            file=sys.stderr,
        )

    return result


def build_gemini_env() -> dict[str, str]:
    """构建 Gemini 调用所需的环境变量

    仿照 build_coder_env 模式：os.environ.copy() + 从 ~/.gemini/.env 强制覆盖白名单键。
    优先级：.gemini/.env 值 > 父进程继承值

    Returns:
        包含所有环境变量的字典
    """
    env = os.environ.copy()
    checked: list[str] = [str(p) for p in _gemini_env_candidates()]

    # 清理父进程 Claude Code 干扰变量
    for var in _PARENT_CLAUDE_VARS:
        env.pop(var, None)

    # 从 ~/.gemini/.env 强制覆盖白名单键（不检查是否已存在）
    for key, value in _load_gemini_dotenv().items():
        if key in _GEMINI_ENV_KEYS:
            env[key] = value

    if not env.get("GEMINI_API_KEY") and not env.get("GOOGLE_API_KEY"):
        print(
            f"[ccg-mcp] Gemini API key missing after env assembly. checked={checked}",
            file=sys.stderr,
        )

    return env


def ensure_gemini_env() -> None:
    """已弃用：Gemini 环境变量现在通过 build_gemini_env() 按调用构建。

    之前在 import 时注入 os.environ，会导致多实例间全局环境污染。
    现在为 no-op，保留函数签名以保持向后兼容。
    """
    pass


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
    model = _resolve_coder_model(coder_config)
    api_token = coder_config.get("api_token", "")

    env_block: dict[str, str] = {
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

    # 合并用户自定义 [coder.env]（用户值优先级更高，会覆盖上面的默认值）
    # Claude CLI 加载 --settings 中的 env 块时会覆盖进程环境变量，
    # 因此必须在这里合并，否则 [coder.env] 里的关键变量会被丢弃
    for key, value in coder_config.get("env", {}).items():
        if value is None:
            continue
        env_block[key] = str(value)

    return json.dumps({"env": env_block}, ensure_ascii=False)


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
