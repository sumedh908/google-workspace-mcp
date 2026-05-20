# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                          # install / refresh dependencies
uv run pytest                    # run all tests
uv run pytest tests/test_runner.py -v          # run a single test file
uv run pytest tests/test_gmail_tools.py::TestGmailSend::test_happy_path -v  # run one test

uv run google-mcp --transport stdio            # start server (stdio)
uv run google-mcp --transport sse --port 8080  # start server (HTTP/SSE)
```

## Architecture

### Request flow

Every MCP tool call follows the same path:

```
AI client → FastMCP tool function → run_gws(args) → gws CLI subprocess → Google API
```

`runner.py` is the single subprocess boundary. All tools call `run_gws()` and catch `GwsError`; they never call `subprocess` directly.

### How tools are composed onto the server

Each service (`gmail`, `calendar`, `drive`) defines its own `FastMCP("service-name")` instance named `router` in `<service>/tools.py`. The unified server in `server.py` mounts all three with `mcp.mount(router)` — no namespace argument, so tool names stay as `gmail_send`, `calendar_create_event`, etc. (not double-prefixed).

### Error contract

Tools never raise. On `GwsError` they return a `dict` with `{"error": ..., "stderr": ..., "hint": ...}`. The `hint` field is only populated on auth errors (exit code 2) and contains the `gws auth login` reminder. This pattern must be preserved in all new tools.

### gws CLI conventions

- All commands pass `--format json` explicitly. `gws gmail +read` defaults to text — it must be overridden.
- Helper commands (`+triage`, `+send`, `+reply`, `+insert`, `+upload`, `+agenda`) are preferred over raw API resource commands when they exist — they handle encoding, threading, and MIME detection automatically.
- Raw API resource commands (`gws calendar events patch`, `gws drive files list`) take `--params <JSON>` for URL parameters and `--json <JSON>` for request body.
- The exact command reference is in `docs/gws-commands.md`.

### Adding a new tool

1. Add the function to the relevant `<service>/tools.py`, decorated with `@router.tool()`.
2. Add a `TypedDict` for its output shape in `<service>/schemas.py` if the shape is new.
3. Use `Annotated[..., Field(...)]` on every parameter for FastMCP schema generation.
4. Add explicit guard checks (empty string, missing file) that return `{"error": ...}` — Pydantic `Field(min_length=1)` is not enforced when calling the function directly in tests.
5. No changes needed in `server.py` — tools are picked up automatically via `mcp.mount`.

### FastMCP version note

FastMCP 3.x uses `mcp.mount(sub_server, namespace=...)` (not `prefix=` which is deprecated). HTTP transport is started via `mcp.run_http_async(transport="sse", ...)`, not `mcp.run()`.

## Key files

| File | Role |
|---|---|
| `src/google_mcp/runner.py` | All subprocess logic; `GwsError`, `GwsNotFoundError`, `run_gws()` |
| `src/google_mcp/server.py` | Server assembly and CLI entry point |
| `src/google_mcp/<service>/tools.py` | FastMCP tool definitions per service |
| `src/google_mcp/<service>/schemas.py` | TypedDict output shapes per service |
| `docs/gws-commands.md` | Verified gws CLI command surface for all operations |
