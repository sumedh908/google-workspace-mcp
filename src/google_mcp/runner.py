"""Subprocess wrapper for the gws CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

__all__ = ["GwsError", "GwsNotFoundError", "run_gws"]

_GWS_NOT_FOUND_HINT = (
    "gws binary not found on PATH. "
    "Install from https://github.com/googleworkspace/cli"
)

# Exit codes defined by gws
_AUTH_EXIT_CODE = 2


class GwsError(Exception):
    """Raised when gws exits non-zero or returns non-JSON output."""

    def __init__(self, message: str, *, exit_code: int = 1, stderr: str = "") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr
        self.is_auth_error = exit_code == _AUTH_EXIT_CODE


class GwsNotFoundError(GwsError):
    """Raised when the gws binary is not found on PATH."""

    def __init__(self) -> None:
        super().__init__(_GWS_NOT_FOUND_HINT, exit_code=127)


def run_gws(
    args: list[str],
    *,
    timeout: float = 30.0,
    dry_run: bool = False,
) -> Any:
    """Run a gws command and return parsed JSON output.

    Args:
        args: gws subcommand and flags, e.g. ["gmail", "+triage", "--format", "json"].
        timeout: Seconds before the subprocess is killed.
        dry_run: If True, print the command without executing and return None.

    Returns:
        Parsed JSON value (dict, list, or None for empty responses).

    Raises:
        GwsNotFoundError: gws binary is not on PATH.
        GwsError: gws exits non-zero, times out, or returns non-JSON stdout.
    """
    gws_bin = (
        os.environ.get("GWS_PATH")
        or shutil.which("gws")
        or shutil.which("gws", path=os.path.expandvars(r"%APPDATA%\npm"))
    ) or "gws"
    cmd = [gws_bin] + args
    if dry_run:
        print("dry-run:", " ".join(cmd))
        return None

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",  # explicit UTF-8; text=True alone uses system locale on Windows
            timeout=timeout,
        )
    except FileNotFoundError as err:
        raise GwsNotFoundError() from err
    except subprocess.TimeoutExpired as err:
        raise GwsError(
            f"gws timed out after {timeout}s",
            exit_code=1,
            stderr="",
        ) from err

    if result.returncode != 0:
        hint = " (re-run `gws auth login`)" if result.returncode == _AUTH_EXIT_CODE else ""
        raise GwsError(
            f"gws exited {result.returncode}{hint}: {result.stderr.strip()}",
            exit_code=result.returncode,
            stderr=result.stderr,
        )

    stdout = result.stdout.strip()
    if not stdout:
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as err:
        raise GwsError(
            f"unexpected non-JSON output: {stdout[:200]}",
            exit_code=0,
            stderr=result.stderr,
        ) from err
