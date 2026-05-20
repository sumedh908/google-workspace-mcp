"""TypedDict schemas for Gmail gws output."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["GmailSummary", "GmailMessage", "GmailSendResult", "GmailDraftResult"]


class GmailSummary(TypedDict, total=False):
    """Single row returned by gws gmail +triage."""

    id: str
    threadId: str
    subject: str
    from_: str
    date: str
    snippet: str


class GmailMessage(TypedDict, total=False):
    """Full message returned by gws gmail +read --format json."""

    id: str
    subject: str
    from_: str
    to: str
    date: str
    body: str


class GmailSendResult(TypedDict, total=False):
    """Result returned by gws gmail +send."""

    id: str
    threadId: str
    labelIds: list[str]


class GmailDraftResult(TypedDict, total=False):
    """Result returned by gws gmail +send --draft."""

    id: str
    message: GmailSendResult
