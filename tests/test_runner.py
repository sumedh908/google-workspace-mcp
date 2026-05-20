"""Tests for google_mcp.runner."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from google_mcp.runner import GwsError, GwsNotFoundError, run_gws


def _mock_result(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


class TestRunGwsSuccess:
    def test_returns_parsed_dict(self) -> None:
        payload = {"messages": [{"id": "abc", "subject": "Hello"}]}
        with patch("subprocess.run", return_value=_mock_result(json.dumps(payload))):
            assert run_gws(["gmail", "+triage", "--format", "json"]) == payload

    def test_returns_parsed_list(self) -> None:
        payload = [{"id": "1"}, {"id": "2"}]
        with patch("subprocess.run", return_value=_mock_result(json.dumps(payload))):
            assert run_gws(["calendar", "+agenda", "--format", "json"]) == payload

    def test_empty_stdout_returns_none(self) -> None:
        with patch("subprocess.run", return_value=_mock_result("")):
            assert run_gws(["calendar", "events", "delete"]) is None

    def test_stderr_with_exit_0_does_not_raise(self) -> None:
        payload = {"files": []}
        with patch(
            "subprocess.run",
            return_value=_mock_result(json.dumps(payload), stderr="deprecation warning"),
        ):
            assert run_gws(["drive", "files", "list"]) == payload


class TestRunGwsErrors:
    def test_nonzero_exit_raises_gws_error(self) -> None:
        with patch(
            "subprocess.run",
            return_value=_mock_result("", stderr="invalid credentials", returncode=1),
        ):
            with pytest.raises(GwsError) as exc_info:
                run_gws(["gmail", "+triage"])
        assert exc_info.value.exit_code == 1
        assert "invalid credentials" in str(exc_info.value)

    def test_auth_exit_code_sets_flag(self) -> None:
        with patch(
            "subprocess.run",
            return_value=_mock_result("", stderr="auth required", returncode=2),
        ):
            with pytest.raises(GwsError) as exc_info:
                run_gws(["gmail", "+triage"])
        assert exc_info.value.is_auth_error is True
        assert "gws auth login" in str(exc_info.value)

    def test_non_json_stdout_raises_gws_error(self) -> None:
        with patch(
            "subprocess.run",
            return_value=_mock_result("Please log in first", returncode=0),
        ):
            with pytest.raises(GwsError, match="unexpected non-JSON output"):
                run_gws(["gmail", "+triage"])

    def test_binary_not_found_raises_gws_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(GwsNotFoundError):
                run_gws(["gmail", "+triage"])

    def test_timeout_raises_gws_error(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["gws"], timeout=30),
        ):
            with pytest.raises(GwsError, match="timed out"):
                run_gws(["gmail", "+triage"], timeout=30)


class TestRunGwsDryRun:
    def test_dry_run_prints_and_returns_none(self, capsys: pytest.CaptureFixture) -> None:
        result = run_gws(["gmail", "+triage"], dry_run=True)
        assert result is None
        captured = capsys.readouterr()
        assert "dry-run:" in captured.out
        assert "gws" in captured.out
