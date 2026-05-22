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
    folder_id: Annotated[str, Field(description="Drive folder ID to list. Omit to search all of My Drive. Get folder IDs by running this tool with a name query first")] = "",
    page_size: Annotated[int, Field(ge=1, le=1000, description="Max files to return (1–1000, default 50)")] = _DEFAULT_PAGE_SIZE,
    query: Annotated[str, Field(description="Drive search query. Examples: \"name contains 'report'\", \"mimeType='application/pdf'\", \"modifiedTime>'2026-01-01T00:00:00'\"")] = "",
) -> Any:
    """List files and folders in Drive — id, name, MIME type, size, modified time, parents. Trashed files excluded.

    Use: browsing a folder, finding file IDs, searching by name or MIME type.
    Skip: use drive_read_metadata when you already have an id (faster single lookup);
          file content cannot be read — this tool returns metadata only.

    Returns: {files:[{id,name,mimeType,modifiedTime,size?,parents}], nextPageToken?}
    Edges: invalid folder_id → GwsError; Drive may return fewer items than page_size;
           nextPageToken present → more results exist (refine query or raise page_size);
           Google Workspace files (Docs/Sheets/Slides) have no size field.

    Example (folder contents) — folder_id="1aBcD..", page_size=20:
      {files:[{id:"1xYz..",name:"Q1 Report.pdf",mimeType:"application/pdf",
               modifiedTime:"2026-03-01T10:00:00Z",size:"204800",parents:["1aBcD.."]}]}

    Example (search by type) — query="mimeType='application/vnd.google-apps.spreadsheet'":
      {files:[{id:"1sHt..",name:"Budget 2026",mimeType:"application/vnd.google-apps.spreadsheet",...}]}
    """
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
    file_id: Annotated[str, Field(min_length=1, description="Drive file or folder ID — from the 'id' field in drive_list_files output")],
) -> Any:
    """Read metadata for a single Drive file or folder — name, MIME type, size, modified time, parents, web link.

    Use: when you have an id and need file properties or the shareable Drive link.
    Skip: use drive_list_files if you don't have an id yet;
          file content (text/binary) is NOT accessible — this returns metadata only;
          use drive_list_files to enumerate a folder's contents.

    Returns: {id, name, mimeType, modifiedTime, size?, parents, webViewLink}
             webViewLink requires Drive access — it is not a public download URL.
    Edges: invalid or inaccessible id → GwsError (404/403);
           Google Workspace files have no size; folders have mimeType
           'application/vnd.google-apps.folder'.

    Example — file_id="1xYz..":
      {id:"1xYz..",name:"Q1 Report.pdf",mimeType:"application/pdf",
       modifiedTime:"2026-03-01T10:00:00Z",size:"204800",
       parents:["1aBcD.."],webViewLink:"https://drive.google.com/file/d/1xYz../view"}
    """
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
    file_path: Annotated[str, Field(min_length=1, description="Absolute or relative local path to the file. Examples: '/home/user/report.pdf', './data/export.csv'. Must be a file, not a directory")],
    folder_id: Annotated[str, Field(description="Destination folder ID (omit to upload to My Drive root). Get from drive_list_files")] = "",
    name: Annotated[str, Field(description="Target filename in Drive. Omit to use the source file's original name")] = "",
) -> Any:
    """Upload a local file to Google Drive — MIME type auto-detected from extension. Always creates a new file.

    Use: putting a local file (PDF, CSV, image, ZIP, etc.) into Drive for sharing or linking.
    Skip: uploading a directory — upload files individually;
          updating an existing Drive file — this always creates a new file (no overwrite);
          creating Google Workspace native docs (Docs/Sheets/Slides) — use their respective APIs.

    Returns: {id, name, mimeType, size, parents, webViewLink}
    Edges: path not found → {"error":"File not found: <path>"};
           path is directory → {"error":"Path is not a file: <path>"};
           unknown extension → MIME type 'application/octet-stream';
           duplicate names allowed in Drive (two files, different IDs);
           invalid folder_id → GwsError.

    Example (to folder, renamed) — file_path="/home/user/report.pdf",
      folder_id="1aBcD..", name="May 2026 Report.pdf":
        {id:"1nEw..",name:"May 2026 Report.pdf",mimeType:"application/pdf",
         size:"204800",parents:["1aBcD.."],
         webViewLink:"https://drive.google.com/file/d/1nEw../view"}

    Example (to root, original name) — file_path="./export.csv":
        {id:"1cSv..",name:"export.csv",mimeType:"text/csv",size:"8192",
         parents:["root"],webViewLink:"https://drive.google.com/file/d/1cSv../view"}
    """
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
