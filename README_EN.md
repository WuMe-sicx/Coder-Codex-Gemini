# CC · Claude + Codex Collaboration

<div align="center">

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-1.20.0+-green.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)

[中文文档](README.md)

**Claude writes the code. Codex is the independent final reviewer.**

A minimal MCP server that wires **Codex** into Claude Code as a read-only review gate.<br>
Claude does requirement analysis, implementation, and self-testing; Codex reviews only — it never edits.

[Quick Start](#-quick-start) • [Positioning](#-positioning) • [Workflow](#-workflow) • [Tool](#️-tool) • [Configuration](#-configuration)

</div>

---

## 🎯 Positioning

Pared down to a **Claude + Codex two-model collaboration**. With ample quota, the goal is not to save money but: **simple flow, stable context, clear responsibility, controllable code quality.**

- **Writer = Claude**: requirement analysis, task breakdown, implementation, self-testing, fixing per review.
- **Final reviewer = Codex**: independent code review, **review only, never modify**.

> Refactored from the earlier four-model "Coder-Codex-Gemini" design. Coder, Gemini, OpenCode / Sisyphus, and the entire "cheap model does the work, expensive model orchestrates" cost-optimization narrative and multi-model pipeline config have been removed.

### Three iron rules

1. **Codex only reviews — it never edits code or files** (`sandbox="read-only"`).
2. **All edits land through Claude**, so two agents never write files concurrently and clobber each other or the context.
3. **The final gatekeeper ≠ the author.** Codex's review is the last gate; Claude must not self-approve.

---

## 🚀 Quick Start

### Prerequisites

| Dependency | Purpose | Install |
|------------|---------|---------|
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | Host (writes code + orchestrates) | official installer |
| [Codex CLI](https://developers.openai.com/codex/quickstart) | Independent review | official installer + `codex login` |
| [uv](https://github.com/astral-sh/uv) | Python package manager | auto-installed by setup |

> Codex uses its own auth (`codex login` / `OPENAI_API_KEY` / `~/.codex/config.toml`). This server needs **no config file of its own**.

### One-click install

```bash
git clone https://github.com/WuMe-sicx/Coder-Codex-Gemini.git
cd Coder-Codex-Gemini

# macOS / Linux
./setup.sh

# Windows: double-click setup.bat, or
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Setup will: install deps → register the MCP server (named `cc`) → install the `cc-review` skill → append the collaboration protocol to your global `~/.claude/CLAUDE.md`.

### Manual registration

**You cloned this repo (recommended)** — runs the local source directly: no network, no rebuild, edits take effect immediately:

```bash
claude mcp add cc -s user --transport stdio -- \
  uv run --directory /abs/path/Coder-Codex-Gemini cc-mcp
```

> `uv run --directory` runs inside the local project env (auto `uv sync` on first run); no reinstall after `git pull` or code edits.

**No local checkout** (only then go through git, fetched on demand):

```bash
claude mcp add cc -s user --transport stdio -- uvx --refresh \
  --from git+https://github.com/WuMe-sicx/Coder-Codex-Gemini.git cc-mcp
```

Verify with `claude mcp list`, and make sure `codex login` is done.

### Uninstall

```bash
./uninstall.sh      # or uninstall.ps1 / uninstall.bat
```

---

## 🔄 Workflow

### The standard loop

```text
Claude breaks down the requirement
→ Claude writes code and self-tests
→ submit to Codex for independent review
→ Claude fixes each item
→ Codex re-reviews
→ pass (otherwise back to "fix")
```

### When to invoke Codex

- Review after completing **one independently verifiable unit / a related batch of changes** (PR-level granularity) — not after every single line.
- **Mandatory review for critical modules**: auth, payments, data writes, external interfaces, concurrency.
- After a fix, **always re-review** until Codex explicitly returns "pass" (✅ PASS).
- Reuse the **same Codex session** for re-review (pass back the returned `SESSION_ID`) so it keeps its initial findings.

### Fix & retry policy

- Fix **item by item** per Codex's list; touch only the relevant code, don't refactor unrelated parts along the way.
- **At most 2 round-trips** per issue; if still stuck, stop and escalate the disagreement to a human — no infinite loops.

### Review instruction

The `codex` tool ships an equivalent built-in system prompt (checklist: **Correctness / Boundary conditions / Security / Test gaps / Maintainability**, ending with `✅ PASS / ⚠️ OPTIMIZE / ❌ CHANGE`). **You don't need to restate the checklist** in the PROMPT — just embed `git diff --no-color` plus "changed files / purpose / focus of this review" so Codex reviews the actual change precisely, saving tokens and improving accuracy.

> Single send-for-review template: see [`skills/cc-review/codex-guide.md`](skills/cc-review/codex-guide.md).

---

## 🛠️ Tool

The server exposes exactly **one** MCP tool: `codex`.

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `PROMPT` | string | required | review task (embed the git diff) |
| `cd` | Path | required | working directory |
| `sandbox` | enum | `read-only` | fixed to read-only for review |
| `SESSION_ID` | string | `""` | reuse a session to keep context |
| `model` | string | `""` | override the Codex model |
| `image` | List[Path] | `None` | attached images |
| `timeout` | int | 300 | idle timeout (s, no output) |
| `max_duration` | int | 1800 | hard cap (s, 0 = unlimited) |
| `max_retries` | int | 1 | Codex is read-only, safe to retry |
| `return_all_messages` / `return_metrics` / `log_metrics` | bool | False | debug / metrics |

**Return** (success):

```json
{ "success": true, "tool": "codex", "SESSION_ID": "…", "result": "review verdict", "duration": "1m20s" }
```

The verdict ends with one line: `✅ PASS` / `⚠️ OPTIMIZE` (ships, with suggestions) / `❌ CHANGE` (must fix).

On failure it returns `error` / `error_kind` / `error_detail`; the `error_kind` values are listed in
[skills/cc-review/codex-guide.md](skills/cc-review/codex-guide.md).

---

## ⚙️ Configuration

**No config file.** Codex uses its own CLI auth; this server only builds a clean environment for the subprocess at call time (stripping the parent Claude Code interference vars and Anthropic credentials) — see `src/cc_mcp/config.py`.

If Codex isn't logged in:

```bash
codex login
# or
printenv OPENAI_API_KEY | codex login --with-api-key
```

---

## 📦 Project Layout

```
src/cc_mcp/
├── cli.py            # console entry: cc-mcp
├── server.py         # registers the single codex tool
├── config.py         # build_codex_env() only: clean subprocess env
└── tools/codex.py    # Codex subprocess exec, stream parsing, retries, structured errors
skills/cc-review/      # the collaboration skill installed to ~/.claude/skills
templates/cc-global-prompt.md   # protocol appended to the global CLAUDE.md
setup.* / uninstall.*           # three-platform installers
需求文档.md            # the authoritative spec (Chinese)
```

Dev commands: see [CLAUDE.md](CLAUDE.md).

---

## 📄 License

[MIT](LICENSE)
