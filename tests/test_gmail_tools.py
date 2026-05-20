"""Tests for google_mcp.gmail.tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from google_mcp.runner import GwsError
from google_mcp.gmail.tools import (
    gmail_draft,
    gmail_list_inbox,
    gmail_read,
    gmail_reply,
    gmail_search,
    gmail_send,
)

_SUMMARY = [{"id": "abc123", "subject": "Hello", "from_": "alice@example.com", "date": "Mon"}]
_MESSAGE = {"id": "abc123", "subject": "Hello", "from_": "alice@example.com", "body": "Hi!"}
_SEND_RESULT = {"id": "msg1", "threadId": "t1", "labelIds": ["SENT"]}
_DRAFT_RESULT = {"id": "draft1", "message": {"id": "msg1", "threadId": "t1"}}


class TestGmailListInbox:
    def test_happy_path(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SUMMARY) as mock:
            result = gmail_list_inbox(max_results=5)
        assert result == _SUMMARY
        args = mock.call_args[0][0]
        assert "--max" in args
        assert "5" in args

    def test_with_query(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SUMMARY) as mock:
            gmail_list_inbox(query="from:boss")
        args = mock.call_args[0][0]
        assert "--query" in args
        assert "from:boss" in args

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", side_effect=GwsError("api error", exit_code=1)):
            result = gmail_list_inbox()
        assert "error" in result


class TestGmailSearch:
    def test_happy_path(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SUMMARY) as mock:
            result = gmail_search(query="is:unread")
        assert result == _SUMMARY
        args = mock.call_args[0][0]
        assert "is:unread" in args

    def test_empty_query_returns_error_dict(self) -> None:
        result = gmail_search(query="")
        assert "error" in result
        assert "empty" in result["error"]

    def test_auth_error_includes_hint(self) -> None:
        with patch(
            "google_mcp.gmail.tools.run_gws",
            side_effect=GwsError("auth", exit_code=2, stderr="auth required"),
        ):
            result = gmail_search(query="test")
        assert "hint" in result
        assert "gws auth login" in result["hint"]


class TestGmailRead:
    def test_happy_path(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_MESSAGE) as mock:
            result = gmail_read(message_id="abc123")
        assert result == _MESSAGE
        args = mock.call_args[0][0]
        assert "--id" in args
        assert "abc123" in args
        assert "--headers" in args

    def test_html_flag_passed(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_MESSAGE) as mock:
            gmail_read(message_id="abc123", html=True)
        assert "--html" in mock.call_args[0][0]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", side_effect=GwsError("not found", exit_code=1)):
            result = gmail_read(message_id="bad")
        assert "error" in result


class TestGmailSend:
    def test_happy_path(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SEND_RESULT) as mock:
            result = gmail_send(to="a@b.com", subject="Hi", body="Hello")
        assert result == _SEND_RESULT
        args = mock.call_args[0][0]
        assert "--to" in args
        assert "--subject" in args
        assert "--body" in args

    def test_cc_and_html_flags(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SEND_RESULT) as mock:
            gmail_send(to="a@b.com", subject="Hi", body="<b>Hi</b>", cc="c@d.com", html=True)
        args = mock.call_args[0][0]
        assert "--cc" in args
        assert "--html" in args

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", side_effect=GwsError("quota", exit_code=1)):
            result = gmail_send(to="a@b.com", subject="Hi", body="Hello")
        assert "error" in result


class TestGmailDraft:
    def test_happy_path_does_not_send(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_DRAFT_RESULT) as mock:
            result = gmail_draft(to="a@b.com", subject="Draft", body="body")
        assert result == _DRAFT_RESULT
        assert "--draft" in mock.call_args[0][0]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", side_effect=GwsError("error", exit_code=1)):
            result = gmail_draft(to="a@b.com", subject="Draft", body="body")
        assert "error" in result


class TestGmailReply:
    def test_happy_path(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_SEND_RESULT) as mock:
            result = gmail_reply(message_id="tid123", body="Thanks!")
        assert result == _SEND_RESULT
        args = mock.call_args[0][0]
        assert "--message-id" in args
        assert "tid123" in args

    def test_draft_flag_passed(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", return_value=_DRAFT_RESULT) as mock:
            gmail_reply(message_id="tid123", body="Draft reply", draft=True)
        assert "--draft" in mock.call_args[0][0]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.gmail.tools.run_gws", side_effect=GwsError("error", exit_code=1)):
            result = gmail_reply(message_id="bad", body="body")
        assert "error" in result
