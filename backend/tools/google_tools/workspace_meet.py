from typing import Any

from backend.tools.google_tools.workspace_core import WorkspaceApiError, workspace_request


MEET_API = "https://meet.googleapis.com/v2"


async def workspace_meet_create_space(access_type: str = "OPEN") -> dict[str, Any]:
    """Create a Google Meet space and return its joining link."""
    if access_type not in {"OPEN", "TRUSTED", "RESTRICTED"}:
        raise WorkspaceApiError("access_type must be OPEN, TRUSTED, or RESTRICTED")
    result = await workspace_request(
        "POST",
        f"{MEET_API}/spaces",
        json={"config": {"accessType": access_type}},
    )
    return {"space": result}


async def workspace_meet_get_space(space: str) -> dict[str, Any]:
    """Read a Meet space by resource name, meeting code, or meeting URI."""
    value = space.strip()
    if value.startswith("https://meet.google.com/"):
        value = value.rsplit("/", 1)[-1]
    path = value if value.startswith("spaces/") else f"spaces/{value}"
    result = await workspace_request("GET", f"{MEET_API}/{path}")
    return {"space": result}


async def workspace_meet_end_active_conference(space: str) -> dict[str, Any]:
    """End the active conference in a Meet space."""
    path = space if space.startswith("spaces/") else f"spaces/{space}"
    await workspace_request("POST", f"{MEET_API}/{path}:endActiveConference", json={})
    return {"space": path, "status": "ended"}


async def workspace_meet_list_conferences(
    meeting_code: str | None = None,
    active_only: bool = False,
    page_size: int = 100,
) -> dict[str, Any]:
    """List Meet conference records, optionally filtered by meeting code or active state."""
    filters = []
    if meeting_code:
        filters.append(f"space.meeting_code = \"{meeting_code}\"")
    if active_only:
        filters.append("end_time IS NULL")
    result = await workspace_request(
        "GET",
        f"{MEET_API}/conferenceRecords",
        params={"filter": " AND ".join(filters), "pageSize": max(1, min(100, page_size))},
    )
    return {"conference_records": result.get("conferenceRecords", []), "next_page_token": result.get("nextPageToken")}


async def workspace_meet_list_participants(conference_record: str, page_size: int = 100) -> dict[str, Any]:
    """List participants and their joining identities for a Meet conference."""
    result = await workspace_request(
        "GET",
        f"{MEET_API}/{conference_record}/participants",
        params={"pageSize": max(1, min(250, page_size))},
    )
    return {"participants": result.get("participants", []), "next_page_token": result.get("nextPageToken")}


async def workspace_meet_list_participant_sessions(participant: str, page_size: int = 100) -> dict[str, Any]:
    """List a Meet participant's join and leave sessions for attendance timing."""
    result = await workspace_request(
        "GET",
        f"{MEET_API}/{participant}/participantSessions",
        params={"pageSize": max(1, min(250, page_size))},
    )
    return {"participant_sessions": result.get("participantSessions", []), "next_page_token": result.get("nextPageToken")}


async def workspace_meet_list_recordings(conference_record: str) -> dict[str, Any]:
    """List recordings generated for a Meet conference."""
    result = await workspace_request("GET", f"{MEET_API}/{conference_record}/recordings")
    return {"recordings": result.get("recordings", [])}


async def workspace_meet_list_transcripts(conference_record: str) -> dict[str, Any]:
    """List transcripts generated for a Meet conference."""
    result = await workspace_request("GET", f"{MEET_API}/{conference_record}/transcripts")
    return {"transcripts": result.get("transcripts", [])}


async def workspace_meet_list_transcript_entries(transcript: str, page_size: int = 100) -> dict[str, Any]:
    """Read timestamped speaker entries from a Meet transcript."""
    result = await workspace_request(
        "GET",
        f"{MEET_API}/{transcript}/entries",
        params={"pageSize": max(1, min(100, page_size))},
    )
    return {"entries": result.get("transcriptEntries", []), "next_page_token": result.get("nextPageToken")}


MEET_TOOLS = [
    workspace_meet_create_space,
    workspace_meet_get_space,
    workspace_meet_end_active_conference,
    workspace_meet_list_conferences,
    workspace_meet_list_participants,
    workspace_meet_list_participant_sessions,
    workspace_meet_list_recordings,
    workspace_meet_list_transcripts,
    workspace_meet_list_transcript_entries,
]
