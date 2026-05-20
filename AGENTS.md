# AGENTS.md

This file provides guidance to all AI coding assistants (GitHub Copilot, Cursor, Windsurf, Gemini Code Assist, and others) when working in this repository.

## Project Purpose

A Python MCP (Model Context Protocol) server that wraps the [`gws` CLI](https://github.com/googleworkspace/cli) as typed FastMCP tools, enabling AI assistants to interact with Gmail, Google Calendar, and Google Drive through a well-defined interface. The server speaks to Google APIs exclusively via `gws` subprocesses — there are no direct Google API SDK calls anywhere in this codebase.

## Development Environment

**Requires:** Python 3.12+, [UV](https://docs.astral.sh/uv/), [`gws` CLI](https://github.com/googleworkspace/cli) installed and authenticated.

```bash
uv sync                                    # install / refresh all dependencies
gws auth login                             # authenticate gws before running the server
```

## Commands

```bash
# Testing
uv run pytest                              # full test suite (58 tests)
uv run pytest tests/test_runner.py -v      # single test file
uv run pytest tests/test_gmail_tools.py::TestGmailSend::test_happy_path -v  # single test

# Running the server
uv run google-mcp --transport stdio        # stdio (Claude Desktop / MCP CLI)
uv run google-mcp --transport sse --port 8080   # HTTP/SSE (remote clients)
uv run google-mcp --transport http --port 8080  # HTTP streamable

# Verify all tools are registered
uv run python -c "
import asyncio
from google_mcp.server import create_server
mcp = create_server()
tools = asyncio.run(mcp.list_tools())
print([t.name for t in tools])
"
```

## Architecture

### Request flow

```
AI client  →  FastMCP tool function  →  run_gws(args)  →  gws subprocess  →  Google API
```

`runner.py` is the **only** subprocess boundary. All tool functions call `run_gws()` and catch `GwsError`. No tool module ever imports `subprocess`.

### Server assembly

Three independent `FastMCP` sub-servers (one per service) are mounted onto a single unified server at startup:

```python
# server.py
mcp = FastMCP("google-workspace")
mcp.mount(gmail_router)      # tools: gmail_list_inbox, gmail_search, ...
mcp.mount(calendar_router)   # tools: calendar_list_events, ...
mcp.mount(drive_router)      # tools: drive_list_files, ...
```

**Do not pass `namespace=` to `mcp.mount()`** — it would double-prefix tool names (e.g. `gmail_gmail_send`). The `prefix=` parameter is deprecated in FastMCP 3.x; use `namespace=` only when intentional prefixing is desired.

New service modules are wired up solely in `server.py`. The tool functions themselves need no changes.

### Tool module structure

Every service package (`gmail/`, `calendar/`, `drive/`) has the same layout:

| File | Contents |
|---|---|
| `__init__.py` | Exports `router` |
| `tools.py` | `router = FastMCP("service-name")` + all `@router.tool()` functions |
| `schemas.py` | `TypedDict` definitions for gws JSON output shapes |

### Error handling contract

Tools **never raise**. On any `GwsError` they return a structured dict:

```python
{"error": "<message>", "stderr": "<captured stderr>", "hint": "<optional re-auth hint>"}
```

`hint` is non-empty only when `err.is_auth_error` is `True` (gws exit code 2). The `_gws_error_response()` helper is defined identically in each `tools.py` — keep it that way.

For input validation errors (e.g. empty required string), return `{"error": "..."}` before calling `run_gws`. Do not rely on Pydantic `Field(min_length=1)` alone — it is enforced by FastMCP at the MCP protocol layer but **not** when the function is called directly in Python tests.

### gws CLI conventions

- Always pass `--format json`. Exception: `gws calendar events delete` returns an empty body — pass no `--format` flag and treat `None` return as success.
- Prefer `gws` helper commands (`+triage`, `+send`, `+reply`, `+insert`, `+agenda`, `+upload`) over raw resource commands when they exist. Helpers handle MIME encoding, threading headers, and MIME-type detection automatically.
- Raw resource commands use `--params <JSON>` for URL/query parameters and `--json <JSON>` for the request body.
- All exact command signatures are documented in `docs/gws-commands.md`. Verify there before writing new `args` lists.

## Code Conventions

- **Imports:** `from __future__ import annotations` on every file. Order: stdlib → third-party → internal.
- **Types:** Full `Annotated[T, Field(...)]` on every tool parameter. Return type is always `Any` (tools return either data dicts or error dicts).
- **Modules:** Every public module exports `__all__`.
- **Paths:** Use `pathlib.Path` for any filesystem operations (see `drive/tools.py`).
- **f-strings only** — no `%` formatting or `.format()`.

## Testing Patterns

All tests mock at the `run_gws` boundary — never at `subprocess.run` except in `test_runner.py` which tests the runner itself.

```python
# Correct — mock run_gws in tool tests
with patch("google_mcp.gmail.tools.run_gws", return_value=payload):
    result = gmail_list_inbox(max_results=5)

# Correct — mock subprocess.run only in test_runner.py
with patch("subprocess.run", return_value=_mock_result(json.dumps(payload))):
    assert run_gws(["gmail", "+triage"]) == payload
```

Tests are grouped in classes by function under test (`TestGmailSend`, `TestCalendarCreateEvent`, etc.). Each test class covers: a happy path, at least one edge case, and a `GwsError` error path.

## Adding a New Tool

1. Add `TypedDict` output shape to `<service>/schemas.py` if the shape is new.
2. Add the tool function to `<service>/tools.py` decorated with `@router.tool()`.
3. Use `Annotated[T, Field(description="...")]` on every parameter.
4. Guard any required-but-default-empty inputs explicitly before calling `run_gws`.
5. Wrap the `run_gws` call in `try/except GwsError` and return `_gws_error_response(err)`.
6. Add tests covering happy path, edge case, and `GwsError` path in the corresponding `tests/test_<service>_tools.py`.
7. No changes needed in `server.py` — the tool is picked up automatically via the mounted router.

## Out of Scope (v1)

Do not add: Google Chat, Meet, Admin SDK, binary attachment download, Drive file deletion or move, multi-account support, OAuth flow.
