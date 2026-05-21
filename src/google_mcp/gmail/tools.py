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
    query: Annotated[str, Field(description="Gmail search filter — overrides the default is:unread. E.g. 'from:boss subject:urgent', 'after:2025/01/01 has:attachment'")] = "",
    include_labels: Annotated[bool, Field(description="Include label names (e.g. INBOX, STARRED) in each result")] = False,
) -> Any:
    """Fetch inbox emails. Without a query, returns unread messages (is:unread). Passing a query replaces that filter with full Gmail search syntax."""
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
    query: Annotated[str, Field(min_length=1, description="Gmail search query, e.g. 'from:boss is:unread', 'subject:invoice after:2025/01/01'")],
    max_results: Annotated[int, Field(ge=1, le=500, description="Max results to return (1-500)")] = 20,
) -> Any:
    """Search across all Gmail messages using Gmail search syntax. Returns id, subject, from, date, and snippet per match."""
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
    message_id: Annotated[str, Field(min_length=1, description="Gmail message ID — get this from gmail_list_inbox or gmail_search")],
    html: Annotated[bool, Field(description="Return HTML body instead of plain text")] = False,
    include_headers: Annotated[bool, Field(description="Include From, To, Subject, and Date headers in the response")] = True,
) -> Any:
    """Read the full body and headers of a Gmail message by ID. Returns subject, from, to, date, and body text (or HTML)."""
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
    to: Annotated[str, Field(min_length=1, description="Recipient email address(es), comma-separated for multiple")],
    subject: Annotated[str, Field(min_length=1, description="Email subject line")],
    body: Annotated[str, Field(min_length=1, description="Email body — plain text or HTML depending on the html flag")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    bcc: Annotated[str, Field(description="BCC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set to true if body contains HTML markup")] = False,
    sender: Annotated[str, Field(description="Send-as alias address (must be configured in Gmail settings)")] = "",
) -> Any:
    """Compose and immediately send an email. Returns the sent message ID and thread ID."""
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
    to: Annotated[str, Field(min_length=1, description="Recipient email address(es), comma-separated for multiple")],
    subject: Annotated[str, Field(min_length=1, description="Email subject line")],
    body: Annotated[str, Field(min_length=1, description="Email body — plain text or HTML depending on the html flag")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set to true if body contains HTML markup")] = False,
) -> Any:
    """Save a composed email as a Gmail draft without sending. Returns the draft ID."""
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
    message_id: Annotated[str, Field(min_length=1, description="Gmail message ID to reply to — get this from gmail_list_inbox or gmail_search")],
    body: Annotated[str, Field(min_length=1, description="Reply body — plain text or HTML depending on the html flag")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set to true if body contains HTML markup")] = False,
    draft: Annotated[bool, Field(description="Save as draft instead of sending immediately")] = False,
) -> Any:
    """Reply to an existing Gmail thread. In-Reply-To and References headers are set automatically to maintain thread order."""
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
