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

### Tool description standard

Every `@router.tool()` docstring must follow this structure (the docstring is what MCP surfaces to AI clients — completeness here directly affects tool selection quality):

```
<One-sentence purpose — what it does + what it returns.>

Use: <when to call it>.
Skip: <when not to — name the better alternative>.

Returns: <compact shape, e.g. {id, name, mimeType}>
Edges: <key edge cases as semicolon-separated inline list>.

Example — <key params>: <compact output on one line>
```

Required criteria (all five must be present):
1. **Purpose** — one sentence, includes what is returned
2. **Input specs** — types/ranges/formats in `Field(description=...)` on every param
3. **Use / Skip** — explicit when-to and when-not-to with named alternatives
4. **Edges** — empty inputs, invalid IDs, boundary values, documented error shapes
5. **Example** — at least one realistic `param=val` → `{output}` inline pair

### Verifying tools after changes

```bash
# Confirm all tools import and register (no runtime errors)
uv run python -c "
import asyncio
from google_mcp.gmail.tools import router as gmail
from google_mcp.calendar.tools import router as cal
from google_mcp.drive.tools import router as drv
async def check():
    tools = await gmail.list_tools() + await cal.list_tools() + await drv.list_tools()
    print(f'{len(tools)} tools:', [t.name for t in tools])
asyncio.run(check())
"

# Spot-check a specific tool's description as seen by MCP clients
uv run python -c "
import asyncio
from google_mcp.gmail.tools import router as gmail
async def check():
    tools = await gmail.list_tools()
    t = next(x for x in tools if x.name == 'gmail_send')
    print(t.description)
asyncio.run(check())
"
```

Expected: 14 tools across gmail (6), calendar (5), drive (3).

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
