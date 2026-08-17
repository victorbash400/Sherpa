from typing import Any

from backend.tools.google_tools.workspace_core import WorkspaceApiError, workspace_request


CALENDAR_API = "https://www.googleapis.com/calendar/v3"


async def workspace_calendar_list_calendars(max_results: int = 100) -> dict[str, Any]:
    """List calendars available to the connected user."""
    result = await workspace_request(
        "GET",
        f"{CALENDAR_API}/users/me/calendarList",
        params={"maxResults": max(1, min(250, max_results))},
    )
    return {"calendars": result.get("items", [])}


async def workspace_calendar_get_event(event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
    """Read full event details, including attendees, attachments, and meeting links."""
    event = await workspace_request(
        "GET",
        f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
        params={"conferenceDataVersion": 1},
    )
    return {"event": event}


async def workspace_calendar_find_free_time(
    time_min: str,
    time_max: str,
    calendar_ids: list[str] | None = None,
    time_zone: str = "UTC",
) -> dict[str, Any]:
    """Return busy intervals for calendars within an RFC3339 time window."""
    ids = calendar_ids or ["primary"]
    result = await workspace_request(
        "POST",
        f"{CALENDAR_API}/freeBusy",
        json={
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": time_zone,
            "items": [{"id": calendar_id} for calendar_id in ids],
        },
    )
    return {"time_min": result.get("timeMin"), "time_max": result.get("timeMax"), "calendars": result.get("calendars", {})}


async def workspace_calendar_respond_to_event(
    event_id: str,
    response_status: str,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Accept, decline, or tentatively accept an event invitation."""
    if response_status not in {"accepted", "declined", "tentative"}:
        raise WorkspaceApiError("response_status must be accepted, declined, or tentative")
    current = await workspace_request(
        "GET",
        f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
    )
    attendees = current.get("attendees", [])
    if not any(attendee.get("self") for attendee in attendees):
        raise WorkspaceApiError("The connected user is not an attendee on this event.")
    updated = [
        {
            "email": attendee.get("email"),
            "responseStatus": response_status if attendee.get("self") else attendee.get("responseStatus"),
        }
        for attendee in attendees
        if attendee.get("email")
    ]
    result = await workspace_request(
        "PATCH",
        f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
        params={"sendUpdates": "all"},
        json={"attendees": updated},
    )
    return {"event_id": result.get("id"), "response_status": response_status, "html_link": result.get("htmlLink")}


CALENDAR_EXTRA_TOOLS = [
    workspace_calendar_list_calendars,
    workspace_calendar_get_event,
    workspace_calendar_find_free_time,
    workspace_calendar_respond_to_event,
]
