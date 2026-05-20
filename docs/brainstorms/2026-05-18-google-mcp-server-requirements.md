# Requirements: Google Workspace MCP Server

**Date:** 2026-05-18
**Status:** draft

## Problem Statement

Developers and AI assistants lack a structured, programmatic interface to interact with Google Workspace (Gmail, Calendar, Drive) via the MCP protocol. The `gws` CLI already provides first-party access to these APIs at runtime, but it is not directly consumable by AI agents or MCP-aware tooling. This server bridges that gap by wrapping `gws` CLI commands as typed MCP tools, enabling AI assistants like Claude to read mail, manage calendar events, and browse Drive files through a well-defined, subprocess-based server.

## Requirements

- R1. The server MUST be implemented in Python 3.12 and managed with the UV package manager.
- R2. All MCP tools MUST be defined using the FastMCP package.
- R3. The server MUST invoke `gws` CLI commands via Python subprocesses (`subprocess.run` / `subprocess.Popen`).
- R4. The server MUST assume `gws` is already authenticated on the host machine; it MUST NOT implement its own OAuth flow.
- R5. Gmail tools MUST support listing the inbox, searching emails by query string, and reading individual email content (subject, sender, body, headers).
- R6. Gmail tools MUST support composing and sending emails, replying to a thread, and saving a draft.
- R7. Calendar tools MUST support listing upcoming events, reading event details, creating new events, updating existing events, and deleting events.
- R8. Drive tools MUST support listing files and folders (with optional path/folder filter), reading file metadata, and file upload.
- R9. Each service (Gmail, Calendar, Drive) MUST be implemented as a separate Python module with its own set of FastMCP tool registrations.
- R10. All subprocess calls MUST capture stdout and stderr; tool responses MUST surface errors as structured MCP error content rather than crashing the server.
- R11. The project MUST include a `pyproject.toml` (UV-compatible) declaring all dependencies and a `uv.lock` file.

## Actors

- A1. AI Assistant (e.g., Claude) — primary consumer that calls MCP tools to read and act on Workspace data on behalf of the user.
- A2. Developer / End User — owns the authenticated `gws` session on the host machine; indirectly benefits from AI actions taken against their Workspace.
- A3. `gws` CLI — first-party Google tool invoked by the server as a subprocess to interact with Workspace APIs.

## Acceptance Examples

- AE1. Given A1 calls the `gmail_list_inbox` tool with `max_results=10`, the server runs `gws gmail messages list` via subprocess and returns a structured list of 10 email summaries (id, subject, sender, date).
- AE2. Given A1 calls `gmail_send` with `to`, `subject`, and `body` fields, the server runs the corresponding `gws gmail messages send` command and returns a success confirmation with the sent message ID.
- AE3. Given A1 calls `calendar_create_event` with title, start time, end time, and optional attendees, the server runs `gws calendar events insert` and returns the newly created event ID and a confirmation.
- AE4. Given A1 calls `drive_list_files` with an optional folder path, the server runs `gws drive files list` and returns file names, IDs, MIME types, and last-modified timestamps.
- AE5. Given the `gws` CLI returns a non-zero exit code (e.g., auth expired, bad arguments), the tool MUST return a structured MCP error response with the stderr output rather than raising an unhandled exception.
- AE6. Given A1 calls `calendar_delete_event` with a valid event ID, the server runs `gws calendar events delete` and returns a confirmation; if the event does not exist, a structured error is returned.

## Out of Scope

- Google Chat and Google Meet integration.
- Admin SDK and org-level user management operations.
- Binary attachment upload or download (no raw file byte handling).
- Multi-account support — the server operates under a single pre-authenticated `gws` session.
- Drive file creation or deletion.
- Google Chat / Meet.

## Open Questions

- [ ] What is the exact `gws` CLI command surface for each operation (need to verify subcommands for `gmail`, `calendar`, `drive` at runtime)?
- [ ] Should tool responses return raw `gws` JSON output parsed into typed dicts, or forward the raw string?
- [ ] Is there a preferred MCP transport (stdio vs. SSE/HTTP) for the target consumer (Claude Desktop vs. other agents)?
- [ ] Should the server expose a single unified MCP server entry point or three separate servers per service?
