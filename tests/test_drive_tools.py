"""Tests for google_mcp.drive.tools."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from google_mcp.runner import GwsError
from google_mcp.drive.tools import drive_list_files, drive_read_metadata, drive_upload_file

_FILE_LIST = {
    "files": [
        {"id": "f1", "name": "report.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-05-01T10:00:00Z"},
        {"id": "f2", "name": "data.csv", "mimeType": "text/csv", "modifiedTime": "2026-05-02T10:00:00Z"},
    ]
}
_FILE_META = {"id": "f1", "name": "report.pdf", "mimeType": "application/pdf", "webViewLink": "https://..."}
_UPLOAD_RESULT = {"id": "new1", "name": "report.pdf", "mimeType": "application/pdf"}


class TestDriveListFiles:
    def test_happy_path(self) -> None:
        with patch("google_mcp.drive.tools.run_gws", return_value=_FILE_LIST):
            result = drive_list_files()
        assert result == _FILE_LIST

    def test_folder_id_added_to_query(self) -> None:
        with patch("google_mcp.drive.tools.run_gws", return_value=_FILE_LIST) as mock:
            drive_list_files(folder_id="folder123")
        args = mock.call_args[0][0]
        params_str = args[args.index("--params") + 1]
        assert "folder123" in params_str

    def test_invalid_folder_returns_error(self) -> None:
        with patch("google_mcp.drive.tools.run_gws", side_effect=GwsError("not found", exit_code=1)):
            result = drive_list_files(folder_id="bad-folder")
        assert "error" in result

    def test_auth_error_includes_hint(self) -> None:
        with patch(
            "google_mcp.drive.tools.run_gws",
            side_effect=GwsError("auth", exit_code=2, stderr="auth required"),
        ):
            result = drive_list_files()
        assert "gws auth login" in result["hint"]


class TestDriveReadMetadata:
    def test_happy_path(self) -> None:
        with patch("google_mcp.drive.tools.run_gws", return_value=_FILE_META) as mock:
            result = drive_read_metadata(file_id="f1")
        assert result == _FILE_META
        args = mock.call_args[0][0]
        assert "f1" in args[args.index("--params") + 1]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.drive.tools.run_gws", side_effect=GwsError("api error", exit_code=1)):
            result = drive_read_metadata(file_id="bad")
        assert "error" in result


class TestDriveUploadFile:
    def test_happy_path(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        with patch("google_mcp.drive.tools.run_gws", return_value=_UPLOAD_RESULT) as mock:
            result = drive_upload_file(file_path=tmp_path)
        assert result == _UPLOAD_RESULT
        args = mock.call_args[0][0]
        assert "+upload" in args

    def test_nonexistent_path_returns_error(self) -> None:
        result = drive_upload_file(file_path="/nonexistent/path/file.txt")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_directory_path_returns_error(self) -> None:
        result = drive_upload_file(file_path="C:/Windows")
        assert "error" in result
        assert "not a file" in result["error"].lower()

    def test_folder_id_passed(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
        with patch("google_mcp.drive.tools.run_gws", return_value=_UPLOAD_RESULT) as mock:
            drive_upload_file(file_path=tmp_path, folder_id="parent123")
        args = mock.call_args[0][0]
        assert "--parent" in args
        assert "parent123" in args

    def test_gws_quota_error_returns_error_dict(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        with patch(
            "google_mcp.drive.tools.run_gws",
            side_effect=GwsError("quota exceeded", exit_code=1, stderr="storageQuotaExceeded"),
        ):
            result = drive_upload_file(file_path=tmp_path)
        assert "error" in result
        assert "quota" in result["error"].lower()
