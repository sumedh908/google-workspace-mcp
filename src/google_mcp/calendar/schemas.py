"""TypedDict schemas for Calendar gws output."""

from __future__ import annotations

from typing import TypedDict

__all__ = ["CalendarEvent", "CalendarEventDetail", "CalendarCreateResult"]


class CalendarEventTime(TypedDict, total=False):
    dateTime: str
    date: str
    timeZone: str


class CalendarAttendee(TypedDict, total=False):
    email: str
    displayName: str
    responseStatus: str


class CalendarEvent(TypedDict, total=False):
    """Summary event row from gws calendar +agenda."""

    id: str
    summary: str
    start: CalendarEventTime
    end: CalendarEventTime
    location: str
    calendarId: str


class CalendarEventDetail(CalendarEvent, total=False):
    """Full event object from gws calendar events get."""

    description: str
    attendees: list[CalendarAttendee]
    htmlLink: str
    status: str
    organizer: dict[str, str]


class CalendarCreateResult(TypedDict, total=False):
    """Result from gws calendar +insert."""

    id: str
    htmlLink: str
    summary: str
    start: CalendarEventTime
    end: CalendarEventTime
