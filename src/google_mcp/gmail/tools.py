"""FastMCP tools for Gmail."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from google_mcp.runner import GwsError, run_gws

__all__ = ["router"]

router = FastMCP("gmail")

_AUTH_HINT = "Re-authenticate by running: gws auth login"


def _gws_error_response(err: GwsError) -> dict[str, Any]:
    hint = f" {_AUTH_HINT}" if err.is_auth_error else ""
    return {"error": str(err), "stderr": err.stderr.strip(), "hint": hint.strip()}


# ---------------------------------------------------------------------------
# List inbox / search
# ---------------------------------------------------------------------------


@dataclass
class ListInboxInput:
    max_results: Annotated[int, Field(ge=1, le=500, default=20)] = 20
    query: Annotated[str, Field(default="")] = ""
    include_labels: bool = False


@router.tool()
def gmail_list_inbox(
    max_results: Annotated[int, Field(ge=1, le=500, description="Max emails to return (1-500)")] = 20,
    query: Annotated[str, Field(description="Gmail search query, e.g. 'is:unread from:boss'")] = "",
    include_labels: Annotated[bool, Field(description="Include label names in output")] = False,
) -> Any:
    """List the inbox (unread by default) or search with a Gmail query."""
    args = ["gmail", "+triage", "--format", "json", "--max", str(max_results)]
    if query:
        args += ["--query", query]
    if include_labels:
        args += ["--labels"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def gmail_search(
    query: Annotated[str, Field(min_length=1, description="Gmail search query string")],
    max_results: Annotated[int, Field(ge=1, le=500, description="Max results")] = 20,
) -> Any:
    """Search Gmail messages using a query string."""
    if not query.strip():
        return {"error": "query must not be empty"}
    args = ["gmail", "+triage", "--format", "json", "--max", str(max_results), "--query", query]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


# ---------------------------------------------------------------------------
# Read a message
# ---------------------------------------------------------------------------


@router.tool()
def gmail_read(
    message_id: Annotated[str, Field(min_length=1, description="Gmail message ID")],
    html: Annotated[bool, Field(description="Return HTML body instead of plain text")] = False,
    include_headers: Annotated[bool, Field(description="Include From/To/Subject/Date headers")] = True,
) -> Any:
    """Read a Gmail message body and headers by message ID."""
    args = ["gmail", "+read", "--id", message_id, "--format", "json"]
    if include_headers:
        args += ["--headers"]
    if html:
        args += ["--html"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


# ---------------------------------------------------------------------------
# Send / reply / draft
# ---------------------------------------------------------------------------


@router.tool()
def gmail_send(
    to: Annotated[str, Field(min_length=1, description="Recipient email(s), comma-separated")],
    subject: Annotated[str, Field(min_length=1, description="Email subject")],
    body: Annotated[str, Field(min_length=1, description="Email body text or HTML")],
    cc: Annotated[str, Field(description="CC recipient(s), comma-separated")] = "",
    bcc: Annotated[str, Field(description="BCC recipient(s), comma-separated")] = "",
    html: Annotated[bool, Field(description="Treat body as HTML")] = False,
    sender: Annotated[str, Field(description="Send-as alias address")] = "",
) -> Any:
    """Compose and send an email."""
    args = ["gmail", "+send", "--to", to, "--subject", subject, "--body", body, "--format", "json"]
    if cc:
        args += ["--cc", cc]
    if bcc:
        args += ["--bcc", bcc]
    if html:
        args += ["--html"]
    if sender:
        args += ["--from", sender]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def gmail_draft(
    to: Annotated[str, Field(min_length=1, description="Recipient email(s), comma-separated")],
    subject: Annotated[str, Field(min_length=1, description="Email subject")],
    body: Annotated[str, Field(min_length=1, description="Email body text or HTML")],
    cc: Annotated[str, Field(description="CC recipient(s), comma-separated")] = "",
    html: Annotated[bool, Field(description="Treat body as HTML")] = False,
) -> Any:
    """Save an email as a draft without sending."""
    args = [
        "gmail", "+send",
        "--to", to, "--subject", subject, "--body", body,
        "--draft", "--format", "json",
    ]
    if cc:
        args += ["--cc", cc]
    if html:
        args += ["--html"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def gmail_reply(
    message_id: Annotated[str, Field(min_length=1, description="Gmail message ID to reply to")],
    body: Annotated[str, Field(min_length=1, description="Reply body text or HTML")],
    cc: Annotated[str, Field(description="CC recipient(s), comma-separated")] = "",
    html: Annotated[bool, Field(description="Treat body as HTML")] = False,
    draft: Annotated[bool, Field(description="Save as draft instead of sending")] = False,
) -> Any:
    """Reply to a Gmail message. Threading is handled automatically."""
    args = ["gmail", "+reply", "--message-id", message_id, "--body", body, "--format", "json"]
    if cc:
        args += ["--cc", cc]
    if html:
        args += ["--html"]
    if draft:
        args += ["--draft"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)
