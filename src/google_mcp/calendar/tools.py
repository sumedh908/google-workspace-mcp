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
    days: Annotated[int, Field(ge=1, le=365, description="Number of days ahead to fetch events for (1-365, default 7)")] = 7,
    calendar: Annotated[str, Field(description="Calendar name or ID to filter to a single calendar (default: all calendars)")] = "",
    timezone: Annotated[str, Field(description="IANA timezone for display, e.g. Asia/Kolkata, America/New_York (defaults to account timezone)")] = "",
) -> Any:
    """List upcoming calendar events across all calendars. Defaults to the next 7 days. Returns event titles, times, locations, and attendees."""
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
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID — get this from calendar_list_events")],
    calendar_id: Annotated[str, Field(description="Calendar ID the event belongs to (default: primary)")] = _DEFAULT_CALENDAR,
) -> Any:
    """Read full details of a calendar event — description, attendees, conferencing links, and recurrence rules."""
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        return run_gws(["calendar", "events", "get", "--params", params, "--format", "json"])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_create_event(
    title: Annotated[str, Field(min_length=1, description="Event title/summary")],
    start: Annotated[str, Field(min_length=1, description="Start time in RFC3339 with timezone offset, e.g. 2026-06-17T09:00:00+05:30")],
    end: Annotated[str, Field(min_length=1, description="End time in RFC3339 with timezone offset, e.g. 2026-06-17T10:00:00+05:30")],
    location: Annotated[str, Field(description="Event location (address, room name, or video link)")] = "",
    description: Annotated[str, Field(description="Event description or agenda (plain text)")] = "",
    attendees: Annotated[list[str], Field(description="List of attendee email addresses to invite")] = [],
    add_meet: Annotated[bool, Field(description="Automatically add a Google Meet video conferencing link")] = False,
    calendar_id: Annotated[str, Field(description="Calendar ID to create the event in (default: primary)")] = _DEFAULT_CALENDAR,
) -> Any:
    """Create a new calendar event. Returns the event ID, Google Calendar link, and conference details if a Meet link was added."""
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
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID to update — get this from calendar_list_events")],
    title: Annotated[str, Field(description="New event title (leave empty to keep existing)")] = "",
    start: Annotated[str, Field(description="New start time in RFC3339, e.g. 2026-06-17T09:00:00+05:30 (leave empty to keep existing)")] = "",
    end: Annotated[str, Field(description="New end time in RFC3339 (leave empty to keep existing)")] = "",
    location: Annotated[str, Field(description="New location (leave empty to keep existing)")] = "",
    description: Annotated[str, Field(description="New description (leave empty to keep existing)")] = "",
    calendar_id: Annotated[str, Field(description="Calendar ID the event belongs to (default: primary)")] = _DEFAULT_CALENDAR,
) -> Any:
    """Patch a calendar event — only the fields you supply are updated, all others are left unchanged."""
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
    event_id: Annotated[str, Field(min_length=1, description="Calendar event ID to delete — get this from calendar_list_events")],
    calendar_id: Annotated[str, Field(description="Calendar ID the event belongs to (default: primary)")] = _DEFAULT_CALENDAR,
) -> Any:
    """Permanently delete a calendar event. This cannot be undone."""
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        run_gws(["calendar", "events", "delete", "--params", params])
        return {"status": "deleted", "eventId": event_id}
    except GwsError as err:
        return _gws_error_response(err)
