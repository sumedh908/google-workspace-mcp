# Google Workspace MCP Server

A Python MCP server that wraps the [`gws` CLI](https://github.com/googleworkspace/cli) as structured FastMCP tools, enabling AI assistants like Claude to interact with Gmail, Google Calendar, and Google Drive through a well-defined interface.

## Overview

The server invokes `gws` CLI commands via Python subprocesses and exposes 14 typed MCP tools across three Google Workspace services. It supports both **stdio transport** (Claude Desktop) and **HTTP/SSE transport** (remote or programmatic access).

> **Note:** This is not an officially supported Google product. The `gws` CLI itself is a community tool — see its [disclaimer](https://github.com/googleworkspace/cli).

---

## Requirements

- Python 3.12+
- [UV package manager](https://docs.astral.sh/uv/)
- [`gws` CLI](https://github.com/googleworkspace/cli) installed and authenticated

---

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd google-mcp

# Install dependencies
uv sync
```

---

## Authentication

This server does **not** handle authentication. It assumes `gws` is already authenticated on the host machine.

To authenticate `gws` before using this server:

```bash
gws auth login
```

If a tool call returns an auth error, re-run `gws auth login` and retry.

---

## Running the Server

### stdio (Claude Desktop)

```bash
uv run google-mcp --transport stdio
```

### HTTP / SSE (remote access or other projects)

```bash
uv run google-mcp --transport sse --port 8080
# or
uv run google-mcp --transport http --port 8080
```

Default host is `127.0.0.1`. Override with `--host`:

```bash
uv run google-mcp --transport sse --host 0.0.0.0 --port 8080
```

---

## Claude Desktop Configuration

Add the following to your `claude_desktop_config.json` (usually at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/google-workspace-mcp",
        "google-mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

Restart Claude Desktop after saving the config. You should see the 14 Google Workspace tools available in the tool picker.

---

## Available Tools

### Gmail (6 tools)

| Tool               | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `gmail_list_inbox` | List inbox emails (unread by default). Supports `max_results` and `query`. |
| `gmail_search`     | Search Gmail using a query string (e.g. `from:boss is:unread`).            |
| `gmail_read`       | Read a message body and headers by message ID.                             |
| `gmail_send`       | Compose and send an email. Supports CC, BCC, HTML body.                    |
| `gmail_reply`      | Reply to a message (threading handled automatically).                      |
| `gmail_draft`      | Save an email as a draft without sending.                                  |

### Calendar (5 tools)

| Tool                    | Description                                                                      |
| ----------------------- | -------------------------------------------------------------------------------- |
| `calendar_list_events`  | List upcoming events. Supports `days`, `calendar` filter, `timezone`.            |
| `calendar_read_event`   | Read full details of a calendar event by ID.                                     |
| `calendar_create_event` | Create a new event. Supports attendees, location, description, Google Meet link. |
| `calendar_update_event` | Update specific fields of an event (patch semantics — only changed fields sent). |
| `calendar_delete_event` | Permanently delete a calendar event.                                             |

### Drive (3 tools)

| Tool                  | Description                                                                   |
| --------------------- | ----------------------------------------------------------------------------- |
| `drive_list_files`    | List files and folders. Supports `folder_id` filter and Drive search `query`. |
| `drive_read_metadata` | Read metadata for a file (name, MIME type, size, modified time, web link).    |
| `drive_upload_file`   | Upload a local file. MIME type auto-detected from extension.                  |

---

## Project Structure

```
google-mcp/
├── pyproject.toml                  # UV-compatible project manifest
├── src/
│   └── google_mcp/
│       ├── __init__.py
│       ├── runner.py               # Shared gws subprocess wrapper
│       ├── server.py               # Unified FastMCP server + CLI entry point
│       ├── gmail/
│       │   ├── __init__.py
│       │   ├── schemas.py          # TypedDict output schemas
│       │   └── tools.py            # FastMCP tool definitions
│       ├── calendar/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   └── tools.py
│       └── drive/
│           ├── __init__.py
│           ├── schemas.py
│           └── tools.py
├── tests/
│   ├── test_runner.py
│   ├── test_gmail_tools.py
│   ├── test_calendar_tools.py
│   ├── test_drive_tools.py
│   └── test_server.py
└── docs/
    ├── gws-commands.md             # gws CLI command reference
    ├── brainstorms/                # Requirements docs
    └── plans/                      # Implementation plans
```

---

## Error Handling

All tools return structured error dictionaries instead of raising exceptions:

```json
{
  "error": "gws exited 2 (re-run `gws auth login`): auth required",
  "stderr": "auth required",
  "hint": "Re-authenticate by running: gws auth login"
}
```

`gws` exit codes surfaced:

| Code | Meaning                                     |
| ---- | ------------------------------------------- |
| 1    | API error from Google                       |
| 2    | Auth error — credentials missing or expired |
| 3    | Validation — bad arguments                  |
| 4    | Discovery error                             |
| 5    | Internal error                              |

---

## Development

### Run tests

```bash
uv run pytest
```

### Run tests with verbose output

```bash
uv run pytest -v
```

### Check registered tools

```python
import asyncio
from google_mcp.server import create_server

mcp = create_server()
tools = asyncio.run(mcp.list_tools())
for t in tools:
    print(t.name, "—", t.description)
```

---

## Connecting from Another Project (HTTP/SSE)

Start the server in HTTP mode:

```bash
uv run google-mcp --transport sse --port 8080
```

Connect via the MCP SSE client in your project:

```python
from fastmcp import Client

async with Client("http://localhost:8080/sse") as client:
    result = await client.call_tool("gmail_list_inbox", {"max_results": 5})
    print(result)
```

---

## Out of Scope (v1)

- Google Chat and Meet
- Admin SDK / org-level user management
- Binary attachment download
- Drive file deletion or move
- Multi-account support
- OAuth flow (use `gws auth login` directly)
