"""Unified Google Workspace MCP server entry point."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from fastmcp import FastMCP

from google_mcp.calendar import router as calendar_router
from google_mcp.drive import router as drive_router
from google_mcp.gmail import router as gmail_router

__all__ = ["create_server", "main"]

_VALID_TRANSPORTS = ("stdio", "http", "sse", "streamable-http")


def create_server() -> FastMCP:
    """Create and return the configured FastMCP server with all tool modules mounted."""
    mcp = FastMCP(
        "google-workspace",
        instructions=(
            "Google Workspace MCP server. Provides tools for Gmail, Google Calendar, "
            "and Google Drive via the gws CLI. Requires a pre-authenticated gws session."
        ),
    )
    mcp.mount(gmail_router)
    mcp.mount(calendar_router)
    mcp.mount(drive_router)
    return mcp


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="google-mcp",
        description="Google Workspace MCP server",
    )
    parser.add_argument(
        "--transport",
        choices=list(_VALID_TRANSPORTS),
        default="stdio",
        help="MCP transport: stdio (default) or http/sse for HTTP server",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP transport (default: 8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> NoReturn:
    """CLI entry point. Parses --transport and starts the appropriate server."""
    args = _parse_args(argv)
    mcp = create_server()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run_http_async(
            transport=args.transport,  # type: ignore[arg-type]
            host=args.host,
            port=args.port,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
