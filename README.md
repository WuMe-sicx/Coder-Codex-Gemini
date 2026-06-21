# CC · Claude + Codex 双模型协作

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-1.20.0+-green.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)

[English Docs](README_EN.md)

**Claude 写代码，Codex 独立终审。**

一个极简的 MCP 服务器：把 **Codex** 作为独立的代码审查闸口接入 Claude Code。<br>
Claude 负责需求分析、编码与自测，Codex 只审不改，做最后一道把关。

[快速开始](#-快速开始) • [定位](#-定位) • [协作流程](#-协作流程) • [工具详解](#️-工具详解) • [配置](#-配置)

</div>

---

## 🎯 定位

精简为 **Claude + Codex 双模型协作**。额度充足，目标不是省钱，而是：**流程简单、上下文稳定、责任清晰、代码质量可控。**

- **主写 = Claude（Max20）**：需求分析、任务拆解、代码实现与修改、自测、按审查意见修复。
- **终审 = Codex（Pro×5）**：独立 Code Review，**只审不改**。

> 本项目由早期的「Coder-Codex-Gemini」四模型方案重构而来，已移除 Coder、Gemini、OpenCode / Sisyphus，以及"便宜模型干活、贵模型调度"的全部成本优化叙事与多模型流水线配置。

### 三条铁律

1. **Codex 默认只审查，绝不直接改代码或文件**（`sandbox="read-only"`）。
2. **所有修改统一由 Claude 落地**，避免两个 agent 同时写文件造成覆盖或上下文混乱。
3. **最终把关的模型 ≠ 写代码的模型** —— Codex 复审是最后一道闸，Claude 不得自我放行。

---

## 🚀 快速开始

### 前置依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | 主体（写代码 + 调度） | 官方安装 |
| [Codex CLI](https://developers.openai.com/codex/quickstart) | 独立审查 | 官方安装 + `codex login` |
| [uv](https://github.com/astral-sh/uv) | Python 包管理 | setup 脚本会自动安装 |

> Codex 使用其自身认证（`codex login` / `OPENAI_API_KEY` / `~/.codex/config.toml`），本服务器**不需要任何配置文件**。

### 一键安装

```bash
git clone https://github.com/WuMe-sicx/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini

# macOS / Linux
./setup.sh

# Windows：双击 setup.bat，或
powershell -ExecutionPolicy Bypass -File setup.ps1
```

setup 会：安装依赖 → 注册 MCP 服务器（名为 `cc`）→ 安装 `cc-review` skill → 把协作协议追加到全局 `~/.claude/CLAUDE.md`。

### 手动注册

**已克隆本仓库（推荐）** —— 直接跑本地源码，**不联网、不打包、改完即生效**：

```bash
claude mcp add cc -s user --transport stdio -- \
  uv run --directory /绝对路径/Coder-Codex-Gemini cc-mcp
```

> `uv run --directory` 在本地项目环境里运行，首次会自动 `uv sync`；之后 `git pull` 或改代码都无需重装。

**没有本地克隆时**（才需要走 git，会按需拉取）：

```bash
claude mcp add cc -s user --transport stdio -- uvx --refresh \
  --from git+https://github.com/WuMe-sicx/Coder-Codex-Gemini.git cc-mcp
```

验证：`claude mcp list`，并确认 `codex login` 已完成。

### 卸载

```bash
./uninstall.sh      # 或 uninstall.ps1 / uninstall.bat
```

---

## 🔄 协作流程

### 标准闭环

```text
Claude 拆解需求
→ Claude 写代码并自测
→ 提交 Codex 独立审查
→ Claude 按意见逐条修复
→ Codex 复审
→ 通过（否则回到「修复」）
```

### 何时调用 Codex 审查

- 完成**一个可独立验证的功能单元 / 一组相关改动后**（PR 级粒度）再送审，不要每改一行就审。
- **关键模块强制送审**：鉴权、支付、数据写入、对外接口、并发逻辑。
- 修复后**必须复审**，直到 Codex 明确回复"通过"（✅ PASS）。
- 复审尽量**复用同一 Codex 会话**（携带返回的 `SESSION_ID`），让它保留初审意见。

### 修复与重试策略

- Claude 依据 Codex 清单**逐条修复**，只改问题相关代码，不顺手重构无关部分。
- 同一问题**最多 2 轮往返**；若仍卡住，停下并把分歧点抛给人工裁决，**不要无限循环**。

### 给 Codex 的审查指令模板

> 请只做独立代码审查，**不要修改代码**。逐项检查并指出「问题 / 位置 / 严重级别 / 建议」：
>
> 1. **逻辑正确性**：是否实现既定需求，有无逻辑漏洞。
> 2. **边界条件**：空值、越界、异常输入、并发竞态。
> 3. **安全风险**：注入、越权、敏感信息泄露、不安全依赖。
> 4. **测试缺口**：关键路径与边界是否有覆盖，断言是否有效。
> 5. **可维护性/性能**：有无明显问题（可选）。
>
> 无问题则明确回复"通过"。

> 调用前先取 `git diff --no-color` 嵌入 PROMPT，让 Codex 精准审查变更，省 token 且更准。

---

## 🛠️ 工具详解

服务器只暴露**一个** MCP 工具：`codex`。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `PROMPT` | string | 必填 | 审核任务描述（建议内嵌 git diff） |
| `cd` | Path | 必填 | 工作目录 |
| `sandbox` | enum | `read-only` | 沙箱策略，审查固定用只读 |
| `SESSION_ID` | string | `""` | 复用会话以保留上下文 |
| `model` | string | `""` | 覆盖 Codex 模型 |
| `image` | List[Path] | `None` | 附加图片 |
| `timeout` | int | 300 | 空闲超时（秒，无输出） |
| `max_duration` | int | 1800 | 总时长上限（秒，0=无限） |
| `max_retries` | int | 1 | Codex 只读，可安全重试 |
| `return_all_messages` / `return_metrics` / `log_metrics` | bool | False | 调试 / 指标 |

**返回值**（成功）：

```json
{ "success": true, "tool": "codex", "SESSION_ID": "…", "result": "审查结论", "duration": "1m20s" }
```

**结论**以一行收尾：`✅ PASS`（通过）/ `⚠️ OPTIMIZE`（可合入，附建议）/ `❌ CHANGE`（必须修复）。

失败时返回 `error` / `error_kind` / `error_detail`，`error_kind` 取值见
[skills/cc-review/codex-guide.md](skills/cc-review/codex-guide.md)。

---

## ⚙️ 配置

**无需配置文件。** Codex 走自己的 CLI 认证；本服务器只在调用时为子进程构建一份干净环境变量（剥离父进程 Claude Code 的干扰变量与 Anthropic 凭证），逻辑见 `src/cc_mcp/config.py`。

如未登录 Codex：

```bash
codex login
# 或
printenv OPENAI_API_KEY | codex login --with-api-key
```

---

## 📦 项目结构

```
src/cc_mcp/
├── cli.py            # 控制台入口 cc-mcp
├── server.py         # 注册唯一的 codex 工具
├── config.py         # 仅 build_codex_env()：清理子进程环境
└── tools/codex.py    # Codex 子进程执行、流式解析、重试、结构化错误
skills/cc-review/      # 安装到 ~/.claude/skills 的协作流程 skill
templates/cc-global-prompt.md   # 追加到全局 CLAUDE.md 的协作协议
setup.* / uninstall.*           # 三平台安装/卸载脚本
需求文档.md            # 双模型方案的权威规格
```

开发命令见 [CLAUDE.md](CLAUDE.md)。

---

## 📄 License

[MIT](LICENSE)
