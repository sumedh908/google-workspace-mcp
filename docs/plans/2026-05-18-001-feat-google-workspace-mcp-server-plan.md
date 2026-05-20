# Plan: Google Workspace MCP Server
**Date:** 2026-05-18
**Status:** approved
**Origin:** docs/brainstorms/2026-05-18-google-mcp-server-requirements.md

## Context
Developers and AI assistants (primarily Claude) need a structured MCP interface to Google Workspace. The `gws` CLI already provides first-party access to Gmail, Calendar, and Drive APIs at runtime. This server wraps those CLI commands as FastMCP tools, enabling AI agents to call typed, structured tools rather than shelling out themselves. The server must support both stdio transport (Claude Desktop) and HTTP/SSE transport (for use from other projects via HTTP).

## Decisions
- **FastMCP** is used for all tool registration. It natively supports both stdio and HTTP/SSE transports.
- **Single unified server** (`server.py`) exposes all Gmail, Calendar, and Drive tools on one `FastMCP` instance.
- **Subprocess runner** (`runner.py`) invokes `gws` via `subprocess.run` with a configurable timeout, captures stdout/stderr, raises `GwsError` on non-zero exit / non-JSON output, raises `GwsNotFoundError` if binary is missing.
- **Parsed typed dicts** returned from all tools. Each service module defines `TypedDict` schemas; runner returns raw dict; tools apply per-command adapters defensively.
- **Pydantic models** for all MCP tool input parameters.
- **Transport default is stdio.** `--transport http --port <N>` enables HTTP/SSE. Falls back to `uvicorn`/Starlette SSE app if FastMCP HTTP transport is unavailable.
- **Auth**: No OAuth flow. Pre-authenticated `gws` session assumed. Auth stderr surfaced as MCP error with re-auth hint.
- **U0 discovery spike** must complete before U3–U5. Exact `gws` subcommand syntax documented in `docs/gws-commands.md`.
- **Module layout**: `src/google_mcp/` with `runner.py`, `gmail/`, `calendar/`, `drive/`, `server.py`.
- **Python 3.12 + UV**: `pyproject.toml` with `requires-python = ">=3.12"`.

## Scope
**In scope:** Gmail (list/search/read/send/reply/draft), Calendar (list/read/create/update/delete), Drive (list/read-metadata/upload), subprocess runner, dual transport, Pydantic inputs, TypedDict outputs, pytest unit tests.

**Out of scope:** Google Chat/Meet, Admin SDK, binary attachment download, Drive delete/move/permissions, multi-account, OAuth flow.

## Implementation Units

- U0. **gws Command Discovery Spike** — `docs/gws-commands.md`
- U1. **Project Scaffold** — `pyproject.toml`, `src/google_mcp/__init__.py`, `tests/__init__.py`
- U2. **Subprocess Runner** — `src/google_mcp/runner.py`
- U3. **Gmail Tools** — `src/google_mcp/gmail/`
- U4. **Calendar Tools** — `src/google_mcp/calendar/`
- U5. **Drive Tools** — `src/google_mcp/drive/`
- U6. **Unified Server Entry Point** — `src/google_mcp/server.py`

## Risks & Dependencies
- gws CLI surface unknown until U0 completes — U3–U5 blocked on U0.
- FastMCP HTTP transport maturity — U6 has Starlette fallback.
- gws JSON schema variance per subcommand — per-command TypedDict adapters in each service module.

## Open Questions
- [ ] Confirm `gws` flags: `--format=json`, `--page-token`, field filtering (resolve in U0).
- [ ] Confirm FastMCP version supports `mcp.run(transport="http")` (resolve in U6).
