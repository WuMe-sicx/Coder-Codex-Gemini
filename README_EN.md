# Coder-Codex-Gemini (CCG)

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-1.20.0+-green.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)

[中文文档](README.md)

**Claude + Coder + Codex + Gemini Multi-Model Collaboration Framework**

Empower **Claude/Sisyphus** as the architect to orchestrate **Coder** for code execution, **Codex** for code quality review, and **Gemini** for expert consultation,<br>forming an **automated multi-party collaboration loop**.

**Supports both Claude Code (MCP) and OpenCode (Oh-My-OpenCode) environments**

[Quick Start](#-quick-start) • [Core Features](#-core-features) • [Architecture](#-architecture) • [Tools Details](#️-tools-details) • [OpenCode Setup](#-opencode-setup)

</div>

---

## 🌟 Core Features

CCG connects multiple top-tier models to build an efficient, cost-effective, and high-quality pipeline for code generation and review:

| Dimension | Value Proposition |
| :--- | :--- |
| **🧠 Cost Optimization** | **Claude/Sisyphus** handles high-intelligence reasoning & orchestration (expensive but powerful), while **Coder** handles heavy lifting of code execution (cost-effective volume). |
| **🧩 Complementary Capabilities** | **Claude** compensates for **Coder**'s creativity gaps, **Codex** provides an independent third-party review perspective, and **Gemini** offers diverse expert opinions. |
| **🛡️ Quality Assurance** | Introduces a dual-review mechanism: **Claude Initial Review** + **Codex Final Review** to ensure code robustness. |
| **🔄 Fully Automated Loop** | Supports a fully automated flow of `Decompose` → `Execute` → `Review` → `Retry`, minimizing human intervention. |
| **🔧 Flexible Architecture** | Supports both **Claude Code (MCP)** and **OpenCode (Oh-My-OpenCode)** environments, choose as needed. |
| **🔄 Context Preservation** | **SESSION_ID** session reuse ensures coherent multi-turn collaboration context, enabling stable execution of long tasks without information loss. |

### 🔀 Two Runtime Environments

| Feature | Claude Code (MCP) | OpenCode (Oh-My-OpenCode) |
|---------|-------------------|---------------------------|
| **Architect** | Claude | Sisyphus (Claude Opus) |
| **Tool Invocation** | MCP Protocol | Sub-agent Delegation |
| **Coder** | claude CLI + Configurable Backend | document-writer Agent |
| **Codex** | codex CLI | oracle Agent |
| **Gemini** | gemini CLI | frontend-ui-ux-engineer Agent |
| **Use Case** | Claude Code Users | Prefer Open Source, Multi-LLM Providers |
| **Config Complexity** | Medium | Higher |

## 🤖 Roles & Collaboration

In this system, each model has a clear responsibility:

*   **Claude**: 👑 **Architect / Coordinator**
    *   Responsible for requirement analysis, task decomposition, prompt optimization, and final decision-making.
*   **Coder**: 🔨 **Executor**
    *   Refers to **high-throughput, execution-oriented** models (e.g., GLM-4.7, DeepSeek-V3, etc.).
    *   Can connect to **any third-party model supporting Claude Code API**, responsible for concrete code generation, modification, and batch task processing.
*   **Codex (OpenAI)**: ⚖️ **Reviewer / Senior Code Consultant**
    *   Responsible for independent code quality control, providing objective Code Reviews, and serving as a consultant for architecture design and complex solutions.
*   **Gemini**: 🧠 **Versatile Expert (Optional)**
    *   A top-tier AI expert on par with Claude. Can serve as senior consultant, independent reviewer, or code executor. Invoked on-demand.

### 📊 Case Study

**[Unit Test Batch Generation](cases/2025-01-05-unit-test-generation/README.md)** - CCG Architecture Real-World Test

| Metric | Pure Claude Approach | CCG Collaborative Approach | Notes |
| :--- | :--- | :--- | :--- |
| **Task Scale** | 7,488 lines of code (481 test cases) | 7,488 lines of code (481 test cases) | Unit test generation for a backend project |
| **Total Cost** | $3.13 | $0.55 | **82% savings** |
| **Claude Cost** | $3.13 | $0.29 | **91% savings** (architecture orchestration only) |
| **Coder Cost** | $0 | $0.26 | Handles heavy code generation tasks |
| **Quality Review** | ❌ No independent review | ✅ Claude Initial Review + Codex Final Review | Dual quality gates, controllable code quality |

**Key Advantages**:
- 💰 **Cost Optimization**: Claude outputs only concise instructions, leveraging cheap input pricing for review work, avoiding expensive code token output
- 🔄 **Context Preservation**: SESSION_ID session reuse mechanism ensures coherent multi-turn collaboration context, enabling stable execution of long tasks
- ⚡ **Long-Task Stability**: Optimized task decomposition and retry strategies ensure stable completion of large tasks (e.g., batch generating 7,488 lines of test code)
- 🛡️ **Quality Assurance**: Dual-review mechanism (Claude Initial Review + Codex Final Review), controllable code quality

### Collaboration Workflow

```mermaid
flowchart TB
    subgraph UserLayer ["User Layer"]
        User(["👤 User Requirement"])
    end

    subgraph ClaudeLayer ["Claude - Architect"]
        Claude["🧠 Analysis & Decomposition"]
        Prompt["📝 Construct Precise Prompt"]
        Review["🔍 Review & Decision"]
    end

    subgraph MCPLayer ["MCP Server"]
        MCP{{"⚙️ CCG-MCP"}}
    end

    subgraph ToolLayer ["Execution Layer"]
        Coder["🔨 Coder Tool<br><code>claude CLI → Configurable Backend</code><br>sandbox: workspace-write"]
        Codex["⚖️ Codex Tool<br><code>codex CLI</code><br>sandbox: read-only"]
        Gemini["🧠 Gemini Tool<br><code>gemini CLI</code><br>sandbox: workspace-write"]
    end

    User --> Claude
    Claude --> Prompt
    Prompt -->|"coder / gemini"| MCP

    MCP -->|"Stream JSON"| Coder
    MCP -->|"Stream JSON"| Gemini

    Coder -->|"SESSION_ID + result"| Review
    Gemini -->|"SESSION_ID + result"| Review

    Review -->|"Needs Review / Expert Opinion"| MCP
    MCP -->|"Stream JSON"| Codex

    Codex -->|"SESSION_ID + Review Verdict"| Review

    Review -->|"✅ Approved"| Done(["🎉 Task Complete"])
    Review -->|"❌ Needs Fix"| Prompt
    Review -->|"⚠️ Minor Optimization"| Claude
```

**Typical Workflow**:

```
1. User submits a requirement
       ↓
2. Claude analyzes, decomposes tasks, constructs precise Prompt
       ↓
3. Calls coder (or gemini) tool → Execute code generation/modification
       ↓
4. Claude reviews results, decides if Codex review or Gemini consultation is needed
       ↓
5. Calls codex (or gemini) tool → Independent Code Review / Get second opinion
       ↓
6. Based on verdict: Approve / Optimize / Re-execute
```

## 🚀 Quick Start

### 1. Prerequisites

Before starting, ensure you have installed the following tools:

*   **uv**: Blazing fast Python package manager ([Installation Guide](https://docs.astral.sh/uv/))
    *   Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
    *   macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
*   **Claude Code**: Version **≥ v2.0.56** ([Installation Guide](https://code.claude.com/docs))
*   **Codex CLI**: Version **≥ v0.61.0** ([Installation Guide](https://developers.openai.com/codex/quickstart))
*   **Gemini CLI** (Optional): Required for Gemini tool ([Installation Guide](https://github.com/google-gemini/gemini-cli))
*   **Coder Backend API Token**: User configuration required. GLM-4.7 is recommended as reference. Get token from [Zhipu AI](https://open.bigmodel.cn).

> **⚠️ Important: Costs & Permissions**
> *   **Authorization**: The `claude`, `codex`, and `gemini` CLI tools must be logged in locally.
> *   **Cost Warning**: Using these tools typically involves subscription fees or API usage costs.
>     *   **Claude Code**: Requires an Anthropic account with billing set up (or 3rd-party integration).
>     *   **Codex CLI**: Requires an OpenAI account or API credits.
>     *   **Gemini CLI**: Defaults to the `gemini-3-pro-preview` model (may involve Google AI subscription or API limits).
>     *   **Coder API**: You are responsible for the API costs of the configured backend model (e.g., Zhipu AI, DeepSeek).
> *   Please ensure all tools are authenticated and account resources are sufficient before use.

### ⚡ One-Click Setup (Recommended)

We provide one-click setup scripts that automate all configuration steps:

**Windows (Double-click or run in terminal)**
```powershell
git clone https://github.com/isYangs/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini
.\setup.bat
```

**macOS/Linux**
```bash
git clone https://github.com/isYangs/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini
chmod +x setup.sh && ./setup.sh
```

**What the script does**:

1. **Check & Install uv** - Auto-downloads if not installed
2. **Check Claude CLI** - Verifies installation
3. **Install Dependencies** - Runs `uv sync`
4. **Register MCP Server** - Configures at user level
5. **Install Skills** - Copies workflow guides to `~/.claude/skills/`
6. **Configure Global Prompt** - Appends to `~/.claude/CLAUDE.md`
7. **Configure Coder** - Interactive input for API Token, Base URL, and Model

**🔐 Security Notes**:
- API Token input is hidden (not displayed on screen)
- Config file saved to `~/.ccg-mcp/config.toml` with user-only read/write permissions
- Tokens are stored locally only, never uploaded or shared

> 💡 **Tip**: After one-click setup completes, restart Claude Code CLI for changes to take effect.

### 🎛️ Configure with CC Switch (GUI)

[CC Switch](https://github.com/farion1231/cc-switch) is a cross-platform desktop tool that provides a unified graphical interface to manage Claude Code, Codex, OpenCode & Gemini CLI, eliminating the need for manual configuration file editing.

#### Install CC Switch

| Platform | Installation Method |
|:---------|:-------------------|
| **Windows** | Download `.msi` installer or portable ZIP from Releases |
| **macOS** | Download `.zip` from [Releases](https://github.com/farion1231/cc-switch/releases) and extract, or `brew tap farion1231/ccswitch && brew install --cask cc-switch` |
| **Linux** | Download `.AppImage` file, add execute permission, and run |

#### Configure CCG in CC Switch

**1. Add MCP Server**

- Open CC Switch, click "MCP" button to enter MCP management panel
- Click "Add Server", select "Custom Configuration"
- Fill in the following information:
  - **Server Name**: `ccg`
  - **Command**: `uvx`
  - **Args**:
    ```
    --refresh
    --from
    git+https://github.com/isYangs/Coder-Codex-Gemini.git
    ccg-mcp
    ```
  - **Transport**: `stdio`
- Check the apps you want to use CCG with (Claude Code, Codex, OpenCode, Gemini CLI)
- Click save, CC Switch will automatically sync the configuration to selected apps

**2. Configure Coder Backend API**

CCG's Coder tool requires backend model API configuration. Please refer to the "Configure Coder" section above, manually create `~/.ccg-mcp/config.toml` file and fill in API Token, Base URL, and Model.

> 💡 **Note**: CC Switch does not directly manage CCG's Coder configuration, manual setup is required.

**3. Install Skills (Optional)**

- Method 1: In CC Switch's Skills Manager, add this project's GitHub repository `https://github.com/isYangs/Coder-Codex-Gemini.git`, select `skills/ccg-workflow` and `skills/gemini-collaboration` to install
- Method 2: Manually copy the `skills/` directory from this project to `~/.claude/skills/`

**4. Configure Global Prompts (Recommended)**

- Create a new preset in CC Switch's Prompts Manager
- Copy the content from `templates/ccg-global-prompt.md` into the preset
- Activate the preset, CC Switch will automatically sync to `~/.claude/CLAUDE.md`

**5. Verify Configuration**

Restart Claude Code CLI, run `claude mcp list` to check if CCG is connected.

#### Key Advantages

| Feature | Description |
|:--------|:------------|
| 🖥️ **Visual Interface** | No manual configuration file editing, intuitive and user-friendly |
| 🔄 **Bidirectional Sync** | Configuration changes automatically sync across multiple AI tools |
| 📦 **One-Click Installation** | MCP servers, Skills, and Prompts deploy automatically |
| ☁️ **Cloud Backup** | Support configuration export/import and cloud synchronization |

> 💡 **Tip**: CC Switch is a third-party tool developed by the community, independent of this project. For issues, please submit to [CC Switch Repository](https://github.com/farion1231/cc-switch).

### 2. Install MCP Server

#### Remote Installation (Recommended)

One-click scripts use remote installation by default. For manual installation:

```bash
claude mcp add ccg -s user --transport stdio -- uvx --refresh --from git+https://github.com/isYangs/Coder-Codex-Gemini.git ccg-mcp
```

#### Local Installation (Development Only)

For source code modification or debugging:

```bash
# Enter project directory
cd /path/to/Coder-Codex-Gemini

# Install dependencies
uv sync

# Register MCP server (using local path)
# Windows
claude mcp add ccg -s user --transport stdio -- uv run --directory $pwd ccg-mcp

# macOS/Linux
claude mcp add ccg -s user --transport stdio -- uv run --directory $(pwd) ccg-mcp
```

#### Remote vs Local Installation

| Feature | Remote (Recommended) | Local |
|---------|---------------------|-------|
| **Stability** | ✅ Independent fetch, no file locking | ⚠️ Multi-terminal conflicts possible |
| **Use Case** | Daily usage | Development/Debug |
| **Skills Support** | Manual install to `~/.claude/skills/` | Manual install (or use one-click script) |
| **Updates** | Auto-fetches latest version | Manual `git pull` required |
| **Dependencies** | Requires `git` command | Only `uv` required |

> **⚠️ Note**: With local installation, multiple terminals calling MCP simultaneously may cause "MCP unresponsive" due to file locking. Remote installation is recommended for daily use.

**Uninstall MCP Server**
```bash
claude mcp remove ccg -s user
```

### 3. Configure Coder

It is recommended to use the **Configuration File** method for management.

> **Configurable Backend**: The Coder tool calls backend models via Claude Code CLI. **User configuration required**. GLM-4.7 is recommended as reference, but you can choose other models supporting Claude Code API (e.g., Minimax, DeepSeek, etc.).

**Create Configuration Directory**:
```bash
# Windows
mkdir %USERPROFILE%\.ccg-mcp

# macOS/Linux
mkdir -p ~/.ccg-mcp
```

**Create Configuration File** `~/.ccg-mcp/config.toml`:
```toml
[coder]
api_token = "your-api-token"  # Required
base_url = "https://open.bigmodel.cn/api/anthropic"  # Example: GLM API
model = "glm-4.7"  # Example: GLM-4.7, can be replaced with other models

[coder.env]
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1"
```

### 4. Install Skills (Recommended)

The Skills layer provides workflow guidance to ensure Claude uses MCP tools correctly.

```bash
# Windows (PowerShell)
if (!(Test-Path "$env:USERPROFILE\.claude\skills")) { mkdir "$env:USERPROFILE\.claude\skills" }
xcopy /E /I "skills\ccg-workflow" "$env:USERPROFILE\.claude\skills\ccg-workflow"
# Optional: Install Gemini collaboration Skill
xcopy /E /I "skills\gemini-collaboration" "$env:USERPROFILE\.claude\skills\gemini-collaboration"

# macOS/Linux
mkdir -p ~/.claude/skills
cp -r skills/ccg-workflow ~/.claude/skills/
# Optional: Install Gemini collaboration Skill
cp -r skills/gemini-collaboration ~/.claude/skills/
```

### 5. Configure Global Prompt (Recommended)

Add mandatory rules to `~/.claude/CLAUDE.md` to ensure Claude follows the collaboration workflow:

```markdown
# Global Protocol

## Mandatory Rules

- **Default Collaboration**: All code/document modification tasks **must** be delegated to Coder for execution, and **must** call Codex for review after milestone completion
- **Skip Requires Confirmation**: If you determine collaboration is unnecessary, **must immediately pause** and report:
  > "This is a simple [description] task, I judge Coder/Codex is not needed. Do you agree? Waiting for your confirmation."
- **Violation = Termination**: Skipping Coder execution or Codex review without confirmation = **workflow violation**
- **Mandatory Session Reuse**: Always save the received `SESSION_ID` and include it in request parameters to maintain context
- **SESSION_ID Management**: Each role (Coder/Codex/Gemini) has independent SESSION_IDs. Always use the actual SESSION_ID returned by MCP tool responses. Never create IDs manually or mix IDs across different roles

## ⚠️ Skill Reading Prerequisite (Mandatory)

**Before calling any CCG MCP tool, you must first execute the corresponding Skill to get best practice guidance:**

| MCP Tool | Prerequisite Skill | Action |
|----------|-------------------|--------|
| `mcp__ccg__coder` | `/ccg-workflow` | Must execute first |
| `mcp__ccg__codex` | `/ccg-workflow` | Must execute first |
| `mcp__ccg__gemini` | `/gemini-collaboration` | Must execute first |

**Execution Flow**:
1. User requests to use Coder/Codex/Gemini
2. **Immediately execute the corresponding Skill** (e.g., `/ccg-workflow`)
3. Read the guidance content returned by the Skill
4. Call MCP tool following the guidance

**Prohibited Behaviors**:
- ❌ Skip Skill and directly call MCP tool
- ❌ Assume you already know best practices without executing Skill

---

# AI Collaboration System

**Claude is the final decision maker**. All AI opinions are for reference only; think critically to make optimal decisions.

## Role Distribution

| Role | Position | Purpose | sandbox | Retry |
|------|----------|---------|---------|-------|
| **Coder** | Code Executor | Generate/modify code, batch tasks | workspace-write | No retry by default |
| **Codex** | Reviewer/Senior Consultant | Architecture design, quality control, Review | read-only | 1 retry by default |
| **Gemini** | Senior Consultant (On-demand) | Architecture design, second opinion, frontend/UI | workspace-write (yolo) | 1 retry by default |

## Core Workflow

1. **Coder Executes**: Delegate all modification tasks to Coder
2. **Claude Verifies**: Quick check after Coder completes; Claude fixes issues directly
3. **Codex Reviews**: Call review after milestone development; if issues found, delegate to Coder for fixes, iterate until passed

## Task Decomposition Principle (Delegating to Coder)

> ⚠️ **One call, one goal**. Do not pile multiple unrelated requirements onto Coder.

- **Precise Prompt**: Clear goal, sufficient context, explicit acceptance criteria
- **Modular Split**: Related changes can be combined; independent modules separated
- **Phased Review**: Claude verifies each module; Codex reviews at milestones

## Pre-coding Preparation (Complex Tasks)

1. Search for affected symbols/entry points
2. List files that need modification
3. For complex issues, consult with Codex or Gemini first

## Gemini Trigger Scenarios

- **User Explicit Request**: User specifies using Gemini
- **Claude Autonomous Call**: When designing frontend/UI, or need second opinion/independent perspective
```

> **Note**: Pure MCP works too, but Skills + Global Prompt configuration is recommended for the best experience.

### 6. Verify Installation

Run the following command to check MCP server status:

```bash
claude mcp list
```

✅ Seeing the following output means installation is successful:
```text
ccg: ... - ✓ Connected
```

### 7. (Optional) Permission Configuration

For a smoother experience, add automatic authorization in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__ccg__coder",
      "mcp__ccg__codex",
      "mcp__ccg__gemini"
    ]
  }
}
```

## 🛠️ Tools Details

### `coder` - Code Executor

Calls configurable backend models to execute specific code generation or modification tasks.

> **Configurable Backend**: The Coder tool calls backend models via Claude Code CLI. **User configuration required**. GLM-4.7 is recommended as reference, but you can choose other models supporting Claude Code API (e.g., Minimax, DeepSeek, etc.).

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `PROMPT` | string | ✅ | - | Specific task instructions and code requirements |
| `cd` | Path | ✅ | - | Target working directory |
| `sandbox` | string | - | `workspace-write` | Sandbox policy, write allowed by default |
| `SESSION_ID` | string | - | `""` | Session ID, used to maintain multi-turn context |
| `return_all_messages` | bool | - | `false` | Whether to return full conversation history (for debugging) |
| `return_metrics` | bool | - | `false` | Whether to include metrics in return value |
| `timeout` | int | - | `300` | Idle timeout (seconds), triggers when no output for this duration |
| `max_duration` | int | - | `1800` | Max duration limit (seconds), default 30 min, 0 for unlimited |
| `max_retries` | int | - | `0` | Max retry count (Coder defaults to no retry) |
| `log_metrics` | bool | - | `false` | Whether to output metrics to stderr |

### `codex` - Code Reviewer

Calls Codex for independent and strict code review.

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `PROMPT` | string | ✅ | - | Review task description |
| `cd` | Path | ✅ | - | Target working directory |
| `sandbox` | string | - | `read-only` | **Forced Read-Only**, reviewer forbidden from modifying code |
| `SESSION_ID` | string | - | `""` | Session ID |
| `skip_git_repo_check` | bool | - | `true` | Whether to allow running in non-Git repositories |
| `return_all_messages` | bool | - | `false` | Whether to return full conversation history (for debugging) |
| `image` | List[Path]| - | `[]` | List of additional images (for UI review, etc.) |
| `model` | string | - | `""` | Specify model, defaults to Codex's own config |
| `return_metrics` | bool | - | `false` | Whether to include metrics in return value |
| `timeout` | int | - | `300` | Idle timeout (seconds), triggers when no output for this duration |
| `max_duration` | int | - | `1800` | Max duration limit (seconds), default 30 min, 0 for unlimited |
| `max_retries` | int | - | `1` | Max retry count (Codex defaults to 1 retry) |
| `log_metrics` | bool | - | `false` | Whether to output metrics to stderr |
| `yolo` | bool | - | `false` | Run all commands without approval (skip sandbox) |
| `profile` | string | - | `""` | Config profile name from ~/.codex/config.toml |

### `gemini` - Versatile Expert (Optional)

Calls Gemini CLI for code execution, technical consultation, or code review. A top-tier AI expert on par with Claude.

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :--- | :--- |
| `PROMPT` | string | ✅ | - | Task instructions with sufficient context |
| `cd` | Path | ✅ | - | Working directory |
| `sandbox` | string | - | `workspace-write` | Sandbox policy, write allowed by default (flexible) |
| `yolo` | bool | - | `true` | Skip approval, enabled by default |
| `SESSION_ID` | string | - | `""` | Session ID for multi-turn conversations |
| `model` | string | - | `gemini-3-pro-preview` | Specify model version |
| `return_all_messages` | bool | - | `false` | Whether to return full conversation history |
| `return_metrics` | bool | - | `false` | Whether to include metrics in return value |
| `timeout` | int | - | `300` | Idle timeout (seconds) |
| `max_duration` | int | - | `1800` | Max duration limit (seconds) |
| `max_retries` | int | - | `1` | Max retry count |
| `log_metrics` | bool | - | `false` | Whether to output metrics to stderr |

**Roles**:
- 🧠 **Senior Consultant**: Architecture design, technology selection, complex solution discussions
- ⚖️ **Independent Reviewer**: Code review, solution evaluation, quality assurance
- 🔨 **Code Executor**: Prototype development, feature implementation (especially frontend/UI)

**Trigger Scenarios**:
- User explicitly requests Gemini
- Claude needs a second opinion or independent perspective

### Timeout Mechanism

This project uses a **dual timeout protection** mechanism:

| Timeout Type | Parameter | Default | Description |
|--------------|-----------|---------|-------------|
| **Idle Timeout** | `timeout` | 300s | Triggers when no output for this duration; resets on activity |
| **Max Duration** | `max_duration` | 1800s | Hard limit from start, forcibly terminates regardless of output |

**Error Type Distinction**:
- `idle_timeout`: Idle timeout (no output)
- `timeout`: Total duration timeout

### Return Value Structure

```json
// Success (default behavior, return_metrics=false)
{
  "success": true,
  "tool": "coder",
  "SESSION_ID": "uuid-string",
  "result": "Response content"
}

// Success (with metrics enabled, return_metrics=true)
{
  "success": true,
  "tool": "coder",
  "SESSION_ID": "uuid-string",
  "result": "Response content",
  "metrics": {
    "ts_start": "2026-01-02T10:00:00.000Z",
    "ts_end": "2026-01-02T10:00:05.123Z",
    "duration_ms": 5123,
    "tool": "coder",
    "sandbox": "workspace-write",
    "success": true,
    "retries": 0,
    "exit_code": 0,
    "prompt_chars": 256,
    "prompt_lines": 10,
    "result_chars": 1024,
    "result_lines": 50,
    "raw_output_lines": 60,
    "json_decode_errors": 0
  }
}

// Failure (structured error, default behavior)
{
  "success": false,
  "tool": "coder",
  "error": "Error summary",
  "error_kind": "idle_timeout | timeout | upstream_error | ...",
  "error_detail": {
    "message": "Error brief",
    "exit_code": 1,
    "last_lines": ["Last 20 lines of output..."],
    "idle_timeout_s": 300,
    "max_duration_s": 1800
    // "retries": 1  // Only returned when retries > 0
  }
}

// Failure (with metrics enabled, return_metrics=true)
{
  "success": false,
  "tool": "coder",
  "error": "Error summary",
  "error_kind": "idle_timeout | timeout | upstream_error | ...",
  "error_detail": {
    "message": "Error brief",
    "exit_code": 1,
    "last_lines": ["Last 20 lines of output..."],
    "idle_timeout_s": 300,
    "max_duration_s": 1800
    // "retries": 1  // Only returned when retries > 0
  },
  "metrics": {
    "ts_start": "2026-01-02T10:00:00.000Z",
    "ts_end": "2026-01-02T10:00:05.123Z",
    "duration_ms": 5123,
    "tool": "coder",
    "sandbox": "workspace-write",
    "success": false,
    "retries": 0,
    "exit_code": 1,
    "prompt_chars": 256,
    "prompt_lines": 10,
    "json_decode_errors": 0
  }
}
```

## 📚 Architecture

### Three-Layer Configuration Architecture (Claude Code)

This project uses a **MCP + Skills + Global Prompt** hybrid architecture in Claude Code environment with clear separation of concerns:

| Layer | Responsibility | Token Usage | Required |
|-------|----------------|-------------|----------|
| **MCP Layer** | Tool implementation (type safety, structured errors, retry, metrics) | Fixed (tool schema) | **Required** |
| **Skills Layer** | Workflow guidance (trigger conditions, process, templates) | On-demand loading | Recommended |
| **Global Prompt Layer** | Mandatory rules (ensure Claude follows collaboration workflow) | Fixed (~20 lines) | Recommended |

**Why is complete configuration recommended?**
- **Pure MCP**: Tools available, but Claude may not understand when/how to use them
- **+ Skills**: Claude learns the workflow, knows when to trigger collaboration
- **+ Global Prompt**: Mandatory rules ensure Claude always follows collaboration discipline

**Token Optimization**: Skills load on-demand, non-code tasks don't load workflow guidance significantly reducing token usage

---

## 🔄 OpenCode Setup

> **OpenCode** is an open-source alternative to Claude Code. Combined with **Oh-My-OpenCode** plugin, it can achieve similar multi-agent orchestration effects. No additional MCP or SKILLS support required.

### Use Cases

- Want to use multiple LLM providers (Claude, GPT, Gemini)
- Need multi-agent parallel collaboration
- Want to see real-time activity of each sub-agent
- Prefer open-source tools

### 🆕 New Users vs Existing Users

| User Type | Recommended Approach | Description |
|-----------|---------------------|-------------|
| **OpenCode not installed** | One-click script | Automatically completes all installation and configuration |
| **OpenCode + Oh-My-OpenCode already installed** | Manual configuration | Reference template files, merge configurations as needed |

> ⚠️ **Note for existing users**: The one-click script will detect existing configuration files and ask whether to overwrite. If you choose to overwrite, original files will be automatically backed up. We recommend skipping and manually merging the required configurations.

### ⚡ One-Click Setup (Recommended for New Users - Those who haven't installed OpenCode)

**Windows (Double-click or run in terminal)**
```powershell
git clone https://github.com/isYangs/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini
.\setup-opencode.bat
```

**macOS/Linux**
```bash
git clone https://github.com/isYangs/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini
chmod +x setup-opencode.sh && ./setup-opencode.sh
```

**What the script does**:

1. **Check & Install Dependencies** - bun, opencode CLI
2. **Install Oh-My-OpenCode** - Interactive subscription selection
3. **Configure opencode.json** - Model definitions and API config
4. **Configure oh-my-opencode.json** - CCG agent role definitions
5. **Configure AGENTS.md** - Collaboration protocol

### 📝 Manual Configuration (Recommended for Existing Users)

If you already have OpenCode and Oh-My-OpenCode installed, we recommend referencing the following template files to manually merge configurations:

| Template File | Target Location | Description |
|---------------|-----------------|-------------|
| [`templates/opencode/opencode.json`](templates/opencode/opencode.json) | `~/.config/opencode/opencode.json` | Model and API config |
| [`templates/opencode/oh-my-opencode.json`](templates/opencode/oh-my-opencode.json) | `~/.config/opencode/oh-my-opencode.json` | Agent role definitions |
| [`templates/opencode/AGENTS.md`](templates/opencode/AGENTS.md) | `~/.config/opencode/AGENTS.md` | Collaboration protocol |

#### Key Configuration Items

**1. `oh-my-opencode.json` - Agent Role Definitions (Key Focus)**

The main items to configure are `prompt_append` and `model` for each agent:

> 💡 **About `prompt_append`**: This is an "append prompt" that adds CCG collaboration rules on top of Oh-My-OpenCode's original prompts. It does not overwrite the original OMO prompts, ensuring maximum compatibility.

```json
{
  "agents": {
    "Sisyphus": {
      "model": "anthropic/claude-opus-4-5-20251101",
      "prompt_append": "## CCG Collaboration Rules\n\nYou are the architect..."
    },
    "document-writer": {
      "model": "zhipuai-coding-plan/glm-4.7",
      "prompt_append": "## ⚠️ Identity Confirmation: You are the Coder sub-agent..."
    },
    "oracle": {
      "model": "openai/gpt-5.1-codex-mini",
      "prompt_append": "## ⚠️ Identity Confirmation: You are the Codex sub-agent..."
    },
    "frontend-ui-ux-engineer": {
      "model": "google/antigravity-gemini-3-pro-high",
      "prompt_append": "## ⚠️ Identity Confirmation: You are the Gemini sub-agent..."
    }
  }
}
```

- **`prompt_append`**: Defines the behavioral norms for each agent role, the core of CCG collaboration
- **`model`**: Can be adjusted to models you have subscribed to

**2. `opencode.json` - Model and API Configuration**

In my personal use case, most models (OpenAI, Google, Zhipu) authenticate via OAuth subscription, requiring no additional API configuration.

**Example for configuring third-party API proxy** (applicable to OpenAI, Claude, and other models):

```json
{
  "provider": {
    "anthropic": {
      "options": {
        "baseURL": "https://your-proxy-api.com/v1",
        "apiKey": "your-api-key"
      },
      "models": {
        "claude-opus-4-5-20251101": { "name": "claude-opus-4-5-20251101" }
      }
    }
  }
}
```

#### ⚠️ Third-Party API Proxy Considerations

When using third-party API proxies, **the model name key must exactly match the model name supported by the proxy**:

```json
// ✅ Correct: Key name matches the proxy's supported model name
"models": {
  "claude-opus-4-5-20251101": { "name": "claude-opus-4-5-20251101" }
}

// ❌ Wrong: Key name doesn't match the proxy, will cause call failures
"models": {
  "my-custom-name": { "name": "claude-opus-4-5-20251101" }
}
```

**Before configuring, confirm**:
1. Which model names your proxy supports
2. Set the key names under `models` to the exact names supported by the proxy
3. When referencing in `oh-my-opencode.json`, use the `provider/model-key` format (e.g., `anthropic/claude-opus-4-5-20251101`)

### Agent Role Mapping (Template configuration, models can be freely changed)

| CCG Role | OpenCode Agent | Model | Responsibility |
|----------|----------------|-------|----------------|
| **Architect** | Sisyphus | Claude Opus 4.5 | Requirement analysis, task decomposition, final decisions |
| **Coder** | document-writer | GLM-4.7 | Code generation, document modification, batch tasks |
| **Codex** | oracle | GPT-5.1 Codex Mini | Code review, architecture consulting, quality control |
| **Gemini** | frontend-ui-ux-engineer | Gemini 3 Pro High | Frontend/UI, second opinions, independent perspective |

### Authentication Setup

After installation, complete authentication for each provider:

```bash
# 1. Anthropic (Claude)
opencode auth login
# → Select: Anthropic → Claude Pro/Max

# 2. OpenAI (ChatGPT/Codex)
opencode auth login
# → Select: OpenAI → ChatGPT Plus/Pro (Codex Subscription)

# 3. Google (Gemini)
opencode auth login
# → Select: Google → OAuth with Google (Antigravity)
```

> ⚠️ **Important**: When using Antigravity plugin, you must set `"google_auth": false` in `oh-my-opencode.json`

### Keyboard Shortcuts

| Shortcut | Function |
|:---------|:---------|
| `Tab` | Toggle build/plan mode |
| `Ctrl+X` then `B` | Toggle Sidebar |
| `Ctrl+X` then `→/←` | Switch subtasks |
| `Ctrl+X` then `↑` | Return to main task |
| `Ctrl+P` | Command palette |

---

## 🧑‍💻 Development & Contribution

Issues and Pull Requests are welcome!

```bash
# 1. Clone repository
git clone https://github.com/isYangs/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini

# 2. Install dependencies (using uv)
uv sync

# 3. Local debug run
uv run ccg-mcp
```

## 📚 References

- **FastMCP**: [GitHub](https://github.com/jlowin/fastmcp) - High-efficiency MCP framework
- **GLM API**: [Zhipu AI](https://open.bigmodel.cn) - Powerful domestic LLM (recommended as Coder backend)
- **Claude Code**: [Documentation](https://docs.anthropic.com/en/docs/claude-code)
- **OpenCode**: [Official Docs](https://opencode.ai/docs) - Open-source AI Coding Agent
- **Oh-My-OpenCode**: [GitHub](https://github.com/code-yeongyu/oh-my-opencode) - OpenCode multi-agent orchestration plugin

## 📄 License

MIT
