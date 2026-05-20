"""FastMCP tools for Google Drive."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from google_mcp.runner import GwsError, run_gws

__all__ = ["router"]

router = FastMCP("drive")

_AUTH_HINT = "Re-authenticate by running: gws auth login"
_DEFAULT_PAGE_SIZE = 50


def _gws_error_response(err: GwsError) -> dict[str, Any]:
    hint = f" {_AUTH_HINT}" if err.is_auth_error else ""
    return {"error": str(err), "stderr": err.stderr.strip(), "hint": hint.strip()}


@router.tool()
def drive_list_files(
    folder_id: Annotated[str, Field(description="Parent folder ID to filter by (omit for root)")] = "",
    page_size: Annotated[int, Field(ge=1, le=1000, description="Max files to return")] = _DEFAULT_PAGE_SIZE,
    query: Annotated[str, Field(description="Drive search query, e.g. \"mimeType='application/pdf'\"")] = "",
) -> Any:
    """List files and folders in Google Drive."""
    q_parts: list[str] = []
    if folder_id:
        q_parts.append(f"'{folder_id}' in parents")
    if query:
        q_parts.append(query)
    q_parts.append("trashed=false")

    params = json.dumps({
        "pageSize": page_size,
        "q": " and ".join(q_parts),
        "fields": "files(id,name,mimeType,modifiedTime,size,parents),nextPageToken",
    })
    try:
        return run_gws(["drive", "files", "list", "--params", params, "--format", "json"])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def drive_read_metadata(
    file_id: Annotated[str, Field(min_length=1, description="Drive file ID")],
) -> Any:
    """Read metadata for a Drive file (name, MIME type, size, modified time, etc.)."""
    params = json.dumps({
        "fileId": file_id,
        "fields": "id,name,mimeType,modifiedTime,size,parents,webViewLink",
    })
    try:
        return run_gws(["drive", "files", "get", "--params", params, "--format", "json"])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def drive_upload_file(
    file_path: Annotated[str, Field(min_length=1, description="Local path to the file to upload")],
    folder_id: Annotated[str, Field(description="Destination folder ID (omit for root)")] = "",
    name: Annotated[str, Field(description="Target filename in Drive (defaults to source filename)")] = "",
) -> Any:
    """Upload a local file to Google Drive. MIME type is auto-detected from the extension."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    if not path.is_file():
        return {"error": f"Path is not a file: {file_path}"}

    args = ["drive", "+upload", str(path), "--format", "json"]
    if folder_id:
        args += ["--parent", folder_id]
    if name:
        args += ["--name", name]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)
