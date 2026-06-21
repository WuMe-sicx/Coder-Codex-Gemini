# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CC (Claude + Codex) is a single-tool MCP server that lets Claude (the writer) hand a finished, self-tested change to **Codex** for independent final review. Codex reviews only — it never modifies code or files. Built with FastMCP, Python 3.12+, transport is stdio.

The collaboration model is deliberately inverted from a prior 4-model design: **Claude writes and self-tests; Codex is the last gate and Claude must not self-approve.** See `需求文档.md` for the authoritative spec and `skills/cc-review/SKILL.md` for the working loop.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the MCP server locally
uv run cc-mcp

# Import sanity check
uv run python -c "import cc_mcp.server"

# Run unit tests (stdlib unittest, no extra deps)
uv run python -m unittest discover -s tests
# single test: uv run python -m unittest tests.test_units.TestResults

# Register with Claude Code (local dev)
claude mcp add cc -s user --transport stdio -- uvx --from "file:$(pwd)" cc-mcp

# Register with Claude Code (remote/production)
claude mcp add cc -s user --transport stdio -- uvx --refresh --from git+https://github.com/WuMe-sicx/Coder-Codex-Gemini.git cc-mcp

# Build distribution
uv build

# One-click setup / uninstall (also installs the skill + global prompt)
./setup.sh        # macOS/Linux  (setup.ps1 / setup.bat on Windows)
./uninstall.sh
```

Unit tests live in `tests/` (stdlib `unittest`, no extra deps) and cover the pure helpers in `errors`/`metrics`/`results`/`process`. No linter is configured. Codex authenticates through its own CLI (`codex login` / `OPENAI_API_KEY` / `~/.codex/config.toml`); this server stores **no** config of its own.

## Architecture

### Entry Flow

`cli.py:main()` → `server.py:run()` → `FastMCP("CC-MCP Server").run(transport="stdio")`

### The one MCP tool

`server.py` registers a single async tool, `codex`, which delegates to `tools/codex.py:codex_tool()`. The tool layer is split into focused modules (each ≤300 lines):

- `tools/codex.py` — `CODEX_SYSTEM_PROMPT` + the `codex_tool()` orchestration loop (build command → stream → parse → retry → assemble result).
- `tools/process.py` — `safe_codex_command()` context manager, process-group helpers, dual-timeout streaming.
- `tools/errors.py` — exceptions, `ErrorKind`, `_build_error_detail`, auth/retry/reconnect predicates.
- `tools/metrics.py` — `MetricsCollector`.
- `tools/results.py` — pure builders for the success / failure result dicts.

| Tool | CLI invoked | Default sandbox | Default retries | Side effects |
|------|-------------|-----------------|-----------------|--------------|
| `codex` | `codex` (OpenAI Codex CLI) | `read-only` | 1 (safe) | No |

### Subprocess execution pattern (tools/process.py + codex.py)

1. **Env isolation**: `config.py:build_codex_env()` copies `os.environ` and strips parent Claude Code interference vars (`CLAUDE_CODE_ENTRYPOINT`, `ANTHROPIC_*`, …) so Claude-side credentials never leak into the OpenAI-backed subprocess. This is the *only* job `config.py` has — there is no config file.
2. **Command construction**: `codex exec --sandbox … --cd … --json`, plus optional `--image/--model/--profile/--yolo/--skip-git-repo-check`; `resume <SESSION_ID>` for multi-turn.
3. **System prompt injection**: Codex CLI has no native system-prompt flag, so `CODEX_SYSTEM_PROMPT` is prepended to the user PROMPT over stdin (`# System … # Task …`). The prompt encodes the review checklist (correctness / boundaries / security / test gaps / maintainability), the Karpathy engineering guidelines (simplicity / surgical scope / explicit assumptions / verifiable success — so Codex reviews on the same bar the author writes under), and the verdict format.
4. **Safe execution**: `safe_codex_command()` context manager wraps `subprocess.Popen(shell=False)` in its own process group, with a background stdout-reading thread feeding an output queue.
5. **Stream parsing**: line-by-line JSONL extracts `thread_id` (the session id), `agent_message` text, and `fail`/`error` events.
6. **Dual timeout**: idle timeout (no output, default 300s) + total duration cap (default 1800s).
7. **Graceful shutdown**: SIGTERM → 5s → SIGKILL → 5s → abandon; 0.3s drain after the `turn.completed` marker.

### Verdict & structured errors

The review ends with exactly one verdict line: `✅ PASS` / `⚠️ OPTIMIZE` / `❌ CHANGE`. Tool results are `Dict[str, Any]` with `success`, and on failure `error`, `error_kind`, `error_detail`. Error kinds: `timeout`, `idle_timeout`, `command_not_found`, `upstream_error`, `auth_required`, `json_decode`, `protocol_missing_session`, `empty_result`, `subprocess_error`, `unexpected_exception`.

### Key design decisions

- **Retry safety**: Codex is read-only, so up to 1 automatic retry is safe (exponential backoff). `command_not_found` and `auth_required` are non-retryable — they need the user.
- **Prompt via stdin**: avoids shell-escaping and length limits for multiline review prompts (including embedded `git diff`).
- **Auth detection**: `_is_auth_error()` scans output for 401 / unauthorized / "not logged in" etc., maps to `auth_required`, and surfaces a `codex login` hint.
- **Metrics**: `MetricsCollector` tracks timing, prompt/result sizes, exit code, retries; optionally emitted to stderr as JSONL via `log_metrics`.

## Repo layout beyond `src/`

- `skills/cc-review/` — the workflow skill installed into `~/.claude/skills` (SKILL.md + codex-guide.md + examples.md + constraint.md). This is the behavioral spec for how Claude should drive the review loop.
- `templates/cc-global-prompt.md` — the `# CC Configuration` block appended to the user's global `~/.claude/CLAUDE.md` by setup.
- `setup.*` / `uninstall.*` — three-platform installers (`.sh`, `.ps1`, `.bat`).

## Code conventions

- Python 3.12+ with type hints; async tool handler in `server.py`, sync internals split across `tools/{codex,process,errors,metrics,results}.py` (one concern per file, ≤300 lines; `codex.py` at ~370 is the documented exception — one cohesive orchestration function plus its MCP schema).
- Tool params use `Annotated[type, Field(...)]` for MCP schema generation.
- Chinese comments and docstrings throughout.
- Error handling uses `CommandTimeoutError` / `CommandNotFoundError` and the `ErrorKind` string constants — never swallow exceptions silently.
