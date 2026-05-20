"""Tests for google_mcp.server."""

from __future__ import annotations

import pytest

from google_mcp.server import _parse_args, create_server


class TestCreateServer:
    def test_all_tools_registered(self) -> None:
        import asyncio

        mcp = create_server()

        async def _get_names() -> list[str]:
            tools = await mcp.list_tools()
            return [t.name for t in tools]

        names = asyncio.run(_get_names())
        assert len(names) == 14

        expected = {
            "gmail_list_inbox", "gmail_search", "gmail_read",
            "gmail_send", "gmail_reply", "gmail_draft",
            "calendar_list_events", "calendar_read_event", "calendar_create_event",
            "calendar_update_event", "calendar_delete_event",
            "drive_list_files", "drive_read_metadata", "drive_upload_file",
        }
        assert set(names) == expected


class TestParseArgs:
    def test_default_transport_is_stdio(self) -> None:
        args = _parse_args([])
        assert args.transport == "stdio"

    def test_http_transport_with_port(self) -> None:
        args = _parse_args(["--transport", "http", "--port", "8080"])
        assert args.transport == "http"
        assert args.port == 8080

    def test_sse_transport(self) -> None:
        args = _parse_args(["--transport", "sse", "--port", "9000"])
        assert args.transport == "sse"

    def test_invalid_transport_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _parse_args(["--transport", "grpc"])
        assert exc_info.value.code != 0

    def test_default_host(self) -> None:
        args = _parse_args([])
        assert args.host == "127.0.0.1"
