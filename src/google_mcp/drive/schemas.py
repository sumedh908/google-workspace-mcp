"""TypedDict schemas for Drive gws output."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["DriveFile", "DriveUploadResult", "DriveFileList"]


class DriveFile(TypedDict, total=False):
    """File metadata returned by drive files list/get."""

    id: str
    name: str
    mimeType: str
    modifiedTime: str
    size: str
    parents: list[str]
    webViewLink: str


class DriveFileList(TypedDict, total=False):
    """Response from gws drive files list."""

    files: list[DriveFile]
    nextPageToken: str


class DriveUploadResult(TypedDict, total=False):
    """Result from gws drive +upload."""

    id: str
    name: str
    mimeType: str
    size: str
    parents: list[str]
    webViewLink: str
