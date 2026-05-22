"""FastMCP tools for Gmail."""

from __future__ import annotations

import html as _html_module
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from google_mcp.runner import GwsError, run_gws

__all__ = ["router"]

router = FastMCP("gmail")

_AUTH_HINT = "Re-authenticate by running: gws auth login"


def _auto_html_body(body: str, html: bool) -> tuple[str, bool]:
    """Convert plain-text body to HTML when it contains newlines.

    Windows passes CLI argument lists through list2cmdline(), which embeds literal
    newlines inside the quoted --body value. CommandLineToArgvW (used by Node.js)
    treats embedded newlines as argument separators, silently truncating everything
    after the first newline. Converting to HTML removes embedded newlines from the
    argument while preserving the visual formatting in the recipient's mail client.

    Returns (processed_body, use_html_flag). A body that is already HTML or contains
    no newlines is returned unchanged.
    """
    if html or "\n" not in body:
        return body, html
    escaped = _html_module.escape(body)
    escaped = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{escaped}</p>", True


def _gws_error_response(err: GwsError) -> dict[str, Any]:
    hint = f" {_AUTH_HINT}" if err.is_auth_error else ""
    return {"error": str(err), "stderr": err.stderr.strip(), "hint": hint.strip()}


@dataclass
class ListInboxInput:
    max_results: Annotated[int, Field(ge=1, le=500, default=20)] = 20
    query: Annotated[str, Field(default="")] = ""
    include_labels: bool = False


@router.tool()
def gmail_list_inbox(
    max_results: Annotated[int, Field(ge=1, le=500, description="Max emails to return (1–500, default 20)")] = 20,
    query: Annotated[str, Field(description="Gmail search filter. Omit → defaults to is:unread. Examples: 'from:boss subject:urgent', 'after:2025/01/01 has:attachment'")] = "",
    include_labels: Annotated[bool, Field(description="Include Gmail label names (INBOX, STARRED, etc.) on each result")] = False,
) -> Any:
    """Fetch a list of inbox messages — id, subject, sender, date, snippet per item.

    Use: browsing recent mail or scanning unread messages without a specific search term.
    Skip: use gmail_search when you have explicit criteria; use gmail_read for full body.

    Returns: list of {id, threadId, subject, from, date, snippet, labels?}
    Edges: omitting query defaults to 'is:unread'; empty list (not error) when no match;
           max_results caps at 500.

    Example — query="from:alice has:attachment", max_results=5:
      [{id:"18f3a..",subject:"Q1 Report",from:"alice@ex.com",date:"2026-05-20",snippet:"See attached..."}]
    """
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
    query: Annotated[str, Field(min_length=1, description="Gmail search query (required, non-empty). Examples: 'from:boss is:unread', 'subject:invoice after:2025/01/01', 'has:attachment larger:5M'")],
    max_results: Annotated[int, Field(ge=1, le=500, description="Max results (1–500, default 20)")] = 20,
) -> Any:
    """Search all Gmail (inbox, sent, archived) with Gmail search syntax — returns snippets, not full bodies.

    Use: finding specific messages anywhere in the mailbox using search operators.
    Skip: use gmail_list_inbox to browse without a query; use gmail_read once you have an id.

    Returns: list of {id, threadId, subject, from, date, snippet}
    Edges: blank query → {"error":"query must not be empty"}; empty list when no match;
           snippets only — call gmail_read for full body.

    Example — query="from:finance@acme.com subject:payroll after:2026/01/01":
      [{id:"19c2d..",subject:"Payroll March 2026",from:"finance@acme.com",date:"2026-03-01",snippet:"..."}]
    """
    if not query.strip():
        return {"error": "query must not be empty"}
    args = ["gmail", "+triage", "--format", "json", "--max", str(max_results), "--query", query]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def gmail_read(
    message_id: Annotated[str, Field(min_length=1, description="Gmail message ID — from the 'id' field in gmail_list_inbox or gmail_search (not threadId)")],
    html: Annotated[bool, Field(description="Return HTML body instead of plain text")] = False,
    include_headers: Annotated[bool, Field(description="Include From, To, Subject, Date headers (default true)")] = True,
) -> Any:
    """Read the full body and headers of a single Gmail message by ID.

    Use: when you have a message id and need complete content (headers + body).
    Skip: call gmail_list_inbox/gmail_search first if you don't have an id;
          use gmail_reply to respond — don't re-send via gmail_send.

    Returns: {id, subject, from, to, date, body} — plain text default, HTML when html=True.
    Edges: invalid/deleted id → GwsError; html=True on plain-text message returns text body.

    Example — message_id="18f3a2b...", include_headers=True:
      {id:"18f3a2b..",subject:"Q1 Report",from:"alice@ex.com",to:"me@ex.com",
       date:"2026-05-20",body:"Hi,\n\nPlease find attached..."}
    """
    args = ["gmail", "+read", "--id", message_id, "--format", "json"]
    if include_headers:
        args += ["--headers"]
    if html:
        args += ["--html"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def gmail_send(
    to: Annotated[str, Field(min_length=1, description="Recipient(s) — comma-separate multiple: 'a@x.com,b@x.com'")],
    subject: Annotated[str, Field(min_length=1, description="Email subject line")],
    body: Annotated[str, Field(min_length=1, description="Body — plain text default; HTML when html=True")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    bcc: Annotated[str, Field(description="BCC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set True when body contains HTML markup")] = False,
    sender: Annotated[str, Field(description="Send-as alias (must be a verified alias in Gmail Settings → Accounts)")] = "",
) -> Any:
    """Compose and immediately send a brand-new email thread.

    Use: starting a fresh conversation with one or more recipients.
    Skip: use gmail_reply for responses (preserves threading headers);
          use gmail_draft to save for review before sending;
          unverified sender alias → API error.

    Returns: {id, threadId, labelIds:["SENT"]}
    Edges: malformed addresses → GwsError from Gmail API; empty cc/bcc ignored.

    Example — to="bob@ex.com", subject="Meeting Tomorrow", body="See you at 10am.":
      {id:"18f3c9..",threadId:"18f3c9..",labelIds:["SENT"]}
    """
    body, html = _auto_html_body(body, html)
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
    to: Annotated[str, Field(min_length=1, description="Recipient(s), comma-separated")],
    subject: Annotated[str, Field(min_length=1, description="Email subject line")],
    body: Annotated[str, Field(min_length=1, description="Body — plain text default; HTML when html=True")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set True when body contains HTML markup")] = False,
) -> Any:
    """Save a new email as a Gmail draft without sending it.

    Use: when the message needs human review before delivery.
    Skip: use gmail_send to deliver immediately;
          use gmail_reply with draft=True to draft a reply (preserves threading);
          BCC not supported here — use gmail_send if BCC is required.

    Returns: {id:<draft_id>, message:{id, threadId, labelIds:["DRAFT"]}}
             Note: draft id ≠ message id — use draft id to locate it in Gmail Drafts.
    Edges: malformed 'to' accepted at save but fails on send; cc ignored if empty.

    Example — to="ceo@ex.com", subject="Q2 Update", body="Highlights...":
      {id:"r123456789",message:{id:"18f3d1..",threadId:"18f3d1..",labelIds:["DRAFT"]}}
    """
    body, html = _auto_html_body(body, html)
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
    message_id: Annotated[str, Field(min_length=1, description="Message ID to reply to — from 'id' field in gmail_list_inbox/gmail_search (not threadId)")],
    body: Annotated[str, Field(min_length=1, description="Reply body — plain text default; HTML when html=True")],
    cc: Annotated[str, Field(description="CC address(es), comma-separated")] = "",
    html: Annotated[bool, Field(description="Set True when body contains HTML markup")] = False,
    draft: Annotated[bool, Field(description="Save as draft instead of sending (threading headers preserved)")] = False,
) -> Any:
    """Reply to an existing Gmail thread — sets In-Reply-To and References headers automatically.

    Use: responding to a received message so the reply stays in the same thread.
    Skip: do NOT use gmail_send for replies — it starts a new thread with broken headers;
          use draft=True to save a threaded draft instead of sending.

    Returns (sent):  {id, threadId, labelIds:["SENT"]}
    Returns (draft): {id:<draft_id>, message:{id, threadId}}
    Edges: must use message id, not threadId — wrong id → GwsError;
           reply to deleted/removed thread → GwsError;
           auto-addressed to original sender; cc adds extra recipients.

    Example (send)  — message_id="18f3a2b..", body="Thanks, will review by EOD.":
      {id:"18f3e5..",threadId:"18f3a2b..",labelIds:["SENT"]}
    Example (draft) — message_id="18f3a2b..", body="Draft...", draft=True:
      {id:"r987654321",message:{id:"18f3f0..",threadId:"18f3a2b.."}}
    """
    body, html = _auto_html_body(body, html)
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
