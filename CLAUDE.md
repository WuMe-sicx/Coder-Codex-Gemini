# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CCG (Coder-Codex-Gemini) is a unified MCP server that enables Claude (Opus) to orchestrate three AI tools: **Coder** (code execution via configurable backend), **Codex** (independent code review via OpenAI), and **Gemini** (expert consultation via Gemini CLI). Built with FastMCP, Python 3.12+, transport is stdio.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the MCP server locally
uv run ccg-mcp

# Register with Claude Code (local dev)
claude mcp add ccg -s user --transport stdio -- uv run --directory $(pwd) ccg-mcp

# Register with Claude Code (remote/production)
claude mcp add ccg -s user --transport stdio -- uvx --refresh --from git+https://github.com/WuMe-sicx/Coder-Codex-Gemini.git ccg-mcp

# Build distribution
uv build
```

No test suite or linter is configured.

## Architecture

### Entry Flow

`cli.py:main()` -> `server.py:run()` -> `FastMCP("CCG-MCP Server").run(transport="stdio")`

### Three MCP Tools (registered in server.py)

Each tool follows the same pattern: **async function in server.py** delegates to **tool module in tools/**, which builds a subprocess command, runs the target CLI, parses streaming JSON output, handles errors/retries, and returns a structured dict.

| Tool | CLI invoked | Default sandbox | Default retries | Side effects |
|------|-------------|-----------------|-----------------|--------------|
| `coder` | `claude` (Claude Code CLI) | `workspace-write` | 0 (writes files) | Yes |
| `codex` | `codex` (OpenAI Codex CLI) | `read-only` | 1 (safe) | No |
| `gemini` | `gemini` (Gemini CLI) | `workspace-write` | 1 | Yes |

### Subprocess Execution Pattern (all three tools share this)

1. **Config loading**: `config.py:get_config()` reads `~/.ccg-mcp/config.toml` (cached at module level)
2. **Environment injection**: `build_coder_env()` / `build_gemini_env()` creates a clean env dict, removing parent process interference vars (`CLAUDE_CODE_ENTRYPOINT`, `ANTHROPIC_MODEL`, etc.)
3. **Command construction**: CLI args assembled with `--print`, `--output-format stream-json`, sandbox flags, system prompt via `--append-system-prompt`, prompt via stdin
4. **Safe execution**: `safe_*_command()` context manager wraps `subprocess.Popen(shell=False)` with background stdout-reading thread + output queue
5. **Stream parsing**: Line-by-line JSONL parsing extracts session ID, assistant text, results, and errors (each CLI has different JSON schema)
6. **Dual timeout**: Idle timeout (default 300s, no output) + total duration cap (default 1800s)
7. **Graceful shutdown**: SIGTERM -> 5s wait -> SIGKILL -> 5s wait -> abandon. 0.3s drain delay after completion marker.

### Configuration Priority

`~/.ccg-mcp/config.toml` > environment variables (`CODER_API_TOKEN`, `CODER_BASE_URL`, `CODER_MODEL`)

Coder config requires: `api_token`, `base_url`, `model` under `[coder]` section. Optional `[coder.env]` for extra env vars.

Gemini reads API keys from `~/.gemini/.env` (whitelist: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_GEMINI_BASE_URL`, `GEMINI_MODEL`).

### Structured Error Returns

All tools return `Dict[str, Any]` with `success`, `error`, `error_kind`, and `error_detail`. Error kinds: `timeout`, `idle_timeout`, `command_not_found`, `upstream_error`, `auth_required`, `json_decode`, `protocol_missing_session`, `empty_result`, `subprocess_error`, `unexpected_exception`.

### Key Design Decisions

- **Parent env cleanup (Coder)**: Explicitly removes vars like `ANTHROPIC_MODEL`, `CLAUDE_CODE_ENTRYPOINT` from subprocess env to prevent parent Claude Code process from interfering with the configured backend.
- **Model aliasing (Coder)**: Maps the configured model to ALL Claude model slots (`ANTHROPIC_DEFAULT_OPUS_MODEL`, `SONNET`, `HAIKU`, `CLAUDE_CODE_SUBAGENT_MODEL`) to ensure the backend model is used regardless of which tier Claude Code selects.
- **Session ID extraction**: Each CLI emits session IDs differently (Coder: `system.init`, Codex: `thread_id`, Gemini: `init` event). Parsed per-tool for conversation continuity.
- **Retry safety**: Coder defaults to 0 retries because it has write side effects. Codex/Gemini default to 1 retry because they're safe (readonly or idempotent).
- **Prompt delivery via stdin**: Supports multiline prompts with no length limit, avoiding shell escaping issues.
- **Metrics via MetricsCollector**: Each tool has its own MetricsCollector tracking timing, prompt/result sizes, exit codes, retries. Optionally logged to stderr as JSONL.

## Code Conventions

- Language: Python 3.12+ with type hints throughout
- Async functions for MCP tool handlers (server.py), sync internals in tool modules
- Tool parameters use `Annotated[type, Field(...)]` for MCP schema generation
- All three tool modules (~950 lines each) share near-identical structure; changes to one likely need mirroring to the others
- Chinese comments and docstrings throughout the codebase
- Error handling uses custom exception classes (`CommandTimeoutError`) and `ErrorKind` string constants
