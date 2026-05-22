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
    days: Annotated[int, Field(ge=1, le=365, description="Days ahead to fetch (1–365, default 7). Use 1 for today only")] = 7,
    calendar: Annotated[str, Field(description="Calendar name or ID to restrict to one calendar (e.g. 'Work', 'personal@gmail.com'). Omit for all calendars")] = "",
    timezone: Annotated[str, Field(description="IANA display timezone (e.g. 'Asia/Kolkata', 'America/New_York'). Omit to use account default")] = "",
) -> Any:
    """List upcoming events across all calendars for the next N days — use this to discover event IDs.

    Use: agenda overview, weekly planning, checking availability.
    Skip: use calendar_read_event when you have an id and need full details
          (description, conferencing link, RSVP statuses).

    Returns: list of {id, summary, start, end, location?, attendees?, calendarId}
    Edges: unrecognised calendar name → GwsError; all-day events have date-only start/end;
           empty list (not error) when no events fall in the window.

    Example — days=3, timezone="Asia/Kolkata":
      [{id:"abc123_20260522",summary:"Standup",
        start:{dateTime:"2026-05-22T10:00:00+05:30"},
        end:{dateTime:"2026-05-22T10:30:00+05:30"},
        attendees:["alice@ex.com","bob@ex.com"]}]
    """
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
    event_id: Annotated[str, Field(min_length=1, description="Event ID — from the 'id' field in calendar_list_events output")],
    calendar_id: Annotated[str, Field(description="Calendar the event belongs to (default 'primary'). Use calendarId from calendar_list_events for secondary calendars")] = _DEFAULT_CALENDAR,
) -> Any:
    """Read complete details of a single calendar event — description, RSVP statuses, Meet link, recurrence rules.

    Use: when you need fields not in calendar_list_events (agenda text, video URL, who accepted).
    Skip: call calendar_list_events first to get an id;
          use calendar_update_event to modify; calendar_delete_event to remove.

    Returns: full event object — {id, summary, description, start, end, location,
             attendees[{email,responseStatus}], conferenceData, recurrence, htmlLink}
    Edges: mismatched event_id + calendar_id → GwsError (404);
           recurring instance ids look like '<base>_<date>' (e.g. 'abc_20260522');
           cancelled instances still return data with status='cancelled'.

    Example — event_id="abc123_20260522":
      {id:"abc123_20260522",summary:"Standup",description:"Daily sync. Agenda:...",
       start:{dateTime:"2026-05-22T10:00:00+05:30"},
       conferenceData:{entryPoints:[{uri:"https://meet.google.com/xyz"}]},
       attendees:[{email:"alice@ex.com",responseStatus:"accepted"}]}
    """
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        return run_gws(["calendar", "events", "get", "--params", params, "--format", "json"])
    except GwsError as err:
        return _gws_error_response(err)


@router.tool()
def calendar_create_event(
    title: Annotated[str, Field(min_length=1, description="Event title shown on the calendar")],
    start: Annotated[str, Field(min_length=1, description="Start time RFC3339 with offset — e.g. '2026-06-17T09:00:00+05:30'. Must be earlier than end")],
    end: Annotated[str, Field(min_length=1, description="End time RFC3339 with offset — e.g. '2026-06-17T10:00:00+05:30'. Must be later than start")],
    location: Annotated[str, Field(description="Address, room name, or video URL. Leave empty to omit")] = "",
    description: Annotated[str, Field(description="Agenda / description in plain text. Leave empty to omit")] = "",
    attendees: Annotated[list[str], Field(description="Attendee email addresses to invite. Empty list → no invites sent")] = [],
    add_meet: Annotated[bool, Field(description="Generate and attach a Google Meet link")] = False,
    calendar_id: Annotated[str, Field(description="Target calendar ID (default 'primary'). Use secondary calendar email for shared calendars")] = _DEFAULT_CALENDAR,
) -> Any:
    """Create a new calendar event and optionally invite attendees or add a Meet link.

    Use: scheduling a meeting, appointment, or reminder.
    Skip: use calendar_update_event for an existing event;
          recurring events require the raw API — this tool creates single instances only.

    Returns: {id, htmlLink, summary, start, end, conferenceData?}
    Edges: start ≥ end → API rejects with error; attendees=[] creates event without invites;
           always include timezone offset in RFC3339 to avoid ambiguity;
           add_meet=True → Meet link in response conferenceData.

    Example (with Meet + attendees) — title="Sprint Planning",
      start="2026-06-17T09:00:00+05:30", end="2026-06-17T10:00:00+05:30",
      attendees=["alice@ex.com"], add_meet=True:
        {id:"xyz789",htmlLink:"https://calendar.google.com/event?eid=..",
         summary:"Sprint Planning",
         conferenceData:{entryPoints:[{uri:"https://meet.google.com/abc-defg-hij"}]}}

    Example (simple reminder, no attendees) — title="Submit report",
      start="2026-06-17T17:00:00+05:30", end="2026-06-17T17:30:00+05:30":
        {id:"rem001",htmlLink:"https://calendar.google.com/event?eid=..",summary:"Submit report"}
    """
    args = [
        "calendar", "+insert",
        "--summary", title,
        "--start", start,
        "--end", end,
        "--format", "json",
        "--calendar", calendar_id,
    ]
    # Normalise location newlines: multi-line addresses become comma-separated.
    # Direct CLI args with embedded \n are truncated by Windows CommandLineToArgvW.
    if location:
        args += ["--location", location.replace("\n", ", ")]
    # Single-line descriptions go via --description; multiline descriptions are
    # patched separately via --json (json.dumps safely escapes \n as \\n).
    multiline_description = description and "\n" in description
    if description and not multiline_description:
        args += ["--description", description]
    for email in attendees:
        args += ["--attendee", email]
    if add_meet:
        args += ["--meet"]
    try:
        result = run_gws(args)
    except GwsError as err:
        return _gws_error_response(err)

    if multiline_description and isinstance(result, dict) and result.get("id"):
        patch_params = json.dumps({"calendarId": calendar_id, "eventId": result["id"]})
        try:
            patched = run_gws([
                "calendar", "events", "patch",
                "--params", patch_params,
                "--json", json.dumps({"description": description}),
                "--format", "json",
            ])
            if isinstance(patched, dict):
                return patched
        except GwsError:
            pass  # event was created; description patch failure is non-fatal
    return result


@router.tool()
def calendar_update_event(
    event_id: Annotated[str, Field(min_length=1, description="Event ID to update — from calendar_list_events")],
    title: Annotated[str, Field(description="New title. Omit to keep existing")] = "",
    start: Annotated[str, Field(description="New start time RFC3339 with offset (e.g. '2026-06-17T09:00:00+05:30'). Omit to keep existing")] = "",
    end: Annotated[str, Field(description="New end time RFC3339 with offset. Omit to keep existing")] = "",
    location: Annotated[str, Field(description="New location. Omit to keep existing")] = "",
    description: Annotated[str, Field(description="New description. Omit to keep existing")] = "",
    calendar_id: Annotated[str, Field(description="Calendar the event belongs to (default 'primary')")] = _DEFAULT_CALENDAR,
) -> Any:
    """Patch specific fields of an existing event — only supplied fields change, all others stay.

    Use: changing time, title, or location without replacing the full event.
    Skip: use calendar_create_event for new events;
          to change attendees or recurrence, delete and recreate — those fields are not patchable here.

    Returns: full updated event object from the Google Calendar API.
    Edges: all fields omitted → {"error":"No fields provided to update"} (no API call made);
           empty string ('') means omit (cannot blank out an existing value via this tool);
           mismatched event_id + calendar_id → GwsError.

    Example (reschedule) — event_id="xyz789",
      start="2026-06-17T11:00:00+05:30", end="2026-06-17T12:00:00+05:30":
        {id:"xyz789",summary:"Sprint Planning",
         start:{dateTime:"2026-06-17T11:00:00+05:30"},
         end:{dateTime:"2026-06-17T12:00:00+05:30"},...}

    Example (rename only) — event_id="xyz789", title="Sprint Planning — Q3":
        {id:"xyz789",summary:"Sprint Planning — Q3",...}
    """
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
    event_id: Annotated[str, Field(min_length=1, description="Event ID to delete — from calendar_list_events. Verify with calendar_read_event before deleting")],
    calendar_id: Annotated[str, Field(description="Calendar the event belongs to (default 'primary')")] = _DEFAULT_CALENDAR,
) -> Any:
    """Permanently delete a calendar event — cannot be undone.

    Use: removing an event you are certain about.
    Skip: use calendar_update_event to reschedule instead of delete;
          call calendar_read_event first when uncertain — there is no trash or undo step;
          deleting a recurring instance id removes only that occurrence; deleting the base
          id may remove the entire series.

    Returns: {status:"deleted", eventId:"<id>"}
    Edges: non-existent or already-deleted id → GwsError (404);
           wrong calendar_id + event_id → GwsError (404);
           removal is immediate from all attendees' calendars.

    Example — event_id="xyz789":
      {status:"deleted",eventId:"xyz789"}
    """
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        run_gws(["calendar", "events", "delete", "--params", params])
        return {"status": "deleted", "eventId": event_id}
    except GwsError as err:
        return _gws_error_response(err)
