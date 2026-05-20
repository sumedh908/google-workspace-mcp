"""FastMCP tools for Google Calendar."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from google_mcp.runner import GwsError, run_gws

__all__ = ["router"]

router = FastMCP("calendar")

_AUTH_HINT = "Re-authenticate by running: gws auth login"
_DEFAULT_CALENDAR = "primary"


def _gws_error_response(err: GwsError) -> dict[str, Any]:
    hint = f" {_AUTH_HINT}" if err.is_auth_error else ""
    return {"error": str(err), "stderr": err.stderr.strip(), "hint": hint.strip()}


@router.tool()
def calendar_list_events(
    days: Annotated[int, Field(ge=1, le=365, description="Number of days ahead to show")] = 7,
    calendar: Annotated[str, Field(description="Calendar name or ID (default: all)")] = "",
    timezone: Annotated[str, Field(description="IANA timezone, e.g. America/New_York")] = "",
) -> Any:
    """List upcoming calendar events."""
    args = ["calendar", "+agenda", "--format", "json", "--days", str(days)]
    if calendar:
        args += ["--calendar", calendar]
    if timezone:
        args += ["--timezone", timezone]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_read_event(
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID")],
    calendar_id: Annotated[str, Field(description="Calendar ID")] = _DEFAULT_CALENDAR,
) -> Any:
    """Read details of a specific calendar event."""
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        return run_gws(["calendar", "events", "get", "--params", params, "--format", "json"])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_create_event(
    title: Annotated[str, Field(min_length=1, description="Event title/summary")],
    start: Annotated[str, Field(min_length=1, description="Start time (RFC3339), e.g. 2026-06-17T09:00:00-07:00")],
    end: Annotated[str, Field(min_length=1, description="End time (RFC3339)")],
    location: Annotated[str, Field(description="Event location")] = "",
    description: Annotated[str, Field(description="Event description")] = "",
    attendees: Annotated[list[str], Field(description="Attendee email addresses")] = [],
    add_meet: Annotated[bool, Field(description="Add a Google Meet link")] = False,
    calendar_id: Annotated[str, Field(description="Calendar ID")] = _DEFAULT_CALENDAR,
) -> Any:
    """Create a new calendar event."""
    args = [
        "calendar", "+insert",
        "--summary", title,
        "--start", start,
        "--end", end,
        "--format", "json",
        "--calendar", calendar_id,
    ]
    if location:
        args += ["--location", location]
    if description:
        args += ["--description", description]
    for email in attendees:
        args += ["--attendee", email]
    if add_meet:
        args += ["--meet"]
    try:
        return run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_update_event(
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID to update")],
    title: Annotated[str, Field(description="New event title")] = "",
    start: Annotated[str, Field(description="New start time (RFC3339)")] = "",
    end: Annotated[str, Field(description="New end time (RFC3339)")] = "",
    location: Annotated[str, Field(description="New location")] = "",
    description: Annotated[str, Field(description="New description")] = "",
    calendar_id: Annotated[str, Field(description="Calendar ID")] = _DEFAULT_CALENDAR,
) -> Any:
    """Update specific fields of a calendar event (patch semantics — only changed fields)."""
    patch: dict[str, Any] = {}
    if title:
        patch["summary"] = title
    if start:
        patch["start"] = {"dateTime": start}
    if end:
        patch["end"] = {"dateTime": end}
    if location:
        patch["location"] = location
    if description:
        patch["description"] = description

    if not patch:
        return {"error": "No fields provided to update"}

    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        return run_gws([
            "calendar", "events", "patch",
            "--params", params,
            "--json", json.dumps(patch),
            "--format", "json",
        ])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_delete_event(
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID to delete")],
    calendar_id: Annotated[str, Field(description="Calendar ID")] = _DEFAULT_CALENDAR,
) -> Any:
    """Delete a calendar event permanently."""
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        run_gws(["calendar", "events", "delete", "--params", params])
        return {"status": "deleted", "eventId": event_id}
    except GwsError as err:
        return _gws_error_response(err)
