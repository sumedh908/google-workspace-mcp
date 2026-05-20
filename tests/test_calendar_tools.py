"""Tests for google_mcp.calendar.tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from google_mcp.runner import GwsError
from google_mcp.calendar.tools import (
    calendar_create_event,
    calendar_delete_event,
    calendar_list_events,
    calendar_read_event,
    calendar_update_event,
)

_EVENTS = [{"id": "evt1", "summary": "Standup", "start": {"dateTime": "2026-05-19T09:00:00Z"}}]
_EVENT_DETAIL = {"id": "evt1", "summary": "Standup", "start": {"dateTime": "2026-05-19T09:00:00Z"}, "htmlLink": "https://..."}
_CREATE_RESULT = {"id": "new1", "htmlLink": "https://...", "summary": "Review"}


class TestCalendarListEvents:
    def test_happy_path(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_EVENTS) as mock:
            result = calendar_list_events(days=7)
        assert result == _EVENTS
        args = mock.call_args[0][0]
        assert "--days" in args
        assert "7" in args

    def test_calendar_filter_passed(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_EVENTS) as mock:
            calendar_list_events(calendar="Work")
        assert "--calendar" in mock.call_args[0][0]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", side_effect=GwsError("api error", exit_code=1)):
            result = calendar_list_events()
        assert "error" in result


class TestCalendarReadEvent:
    def test_happy_path(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_EVENT_DETAIL) as mock:
            result = calendar_read_event(event_id="evt1")
        assert result == _EVENT_DETAIL
        args = mock.call_args[0][0]
        assert "events" in args
        assert "get" in args

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", side_effect=GwsError("not found", exit_code=1)):
            result = calendar_read_event(event_id="bad")
        assert "error" in result


class TestCalendarCreateEvent:
    def test_happy_path(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_CREATE_RESULT) as mock:
            result = calendar_create_event(
                title="Standup",
                start="2026-05-19T09:00:00-07:00",
                end="2026-05-19T09:30:00-07:00",
            )
        assert result == _CREATE_RESULT
        args = mock.call_args[0][0]
        assert "--summary" in args
        assert "Standup" in args

    def test_attendees_and_meet(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_CREATE_RESULT) as mock:
            calendar_create_event(
                title="Review",
                start="2026-05-19T10:00:00Z",
                end="2026-05-19T11:00:00Z",
                attendees=["alice@example.com"],
                add_meet=True,
            )
        args = mock.call_args[0][0]
        assert "--attendee" in args
        assert "--meet" in args

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", side_effect=GwsError("api error", exit_code=1)):
            result = calendar_create_event(title="X", start="2026-05-19T09:00:00Z", end="2026-05-19T10:00:00Z")
        assert "error" in result


class TestCalendarUpdateEvent:
    def test_happy_path_partial_fields(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=_EVENT_DETAIL) as mock:
            result = calendar_update_event(event_id="evt1", title="New Title")
        assert result == _EVENT_DETAIL
        args = mock.call_args[0][0]
        assert "patch" in args

    def test_no_fields_returns_error(self) -> None:
        result = calendar_update_event(event_id="evt1")
        assert "error" in result
        assert "No fields" in result["error"]

    def test_gws_error_returns_error_dict(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", side_effect=GwsError("api error", exit_code=1)):
            result = calendar_update_event(event_id="evt1", title="New")
        assert "error" in result


class TestCalendarDeleteEvent:
    def test_happy_path(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", return_value=None):
            result = calendar_delete_event(event_id="evt1")
        assert result["status"] == "deleted"
        assert result["eventId"] == "evt1"

    def test_nonexistent_event_returns_error(self) -> None:
        with patch("google_mcp.calendar.tools.run_gws", side_effect=GwsError("not found", exit_code=1)):
            result = calendar_delete_event(event_id="bad-id")
        assert "error" in result

    def test_auth_error_includes_hint(self) -> None:
        with patch(
            "google_mcp.calendar.tools.run_gws",
            side_effect=GwsError("auth", exit_code=2, stderr="auth required"),
        ):
            result = calendar_delete_event(event_id="evt1")
        assert "gws auth login" in result["hint"]
