---
name: workspace-scheduling
description: Resolve Google contacts and inspect, create, update, or delete Google Calendar events. Use for scheduling, conflict checks, attendee resolution, and calendar changes.
---

# Calendar and contacts workflow

1. Resolve named people with `workspace_people_search_contacts` when an address is not already explicit. Do not guess between multiple matches.
2. List events over the relevant time window with `workspace_calendar_list_events` before scheduling or moving an event. Check overlaps in the requested timezone.
3. Create with `workspace_calendar_create_event` only after title, start, end, timezone, and attendees are unambiguous.
4. Update or delete only a verified event ID. Treat deletion and invitations as consequential actions; confirm uncertain targets first.
5. Re-list or inspect the result and report the returned event ID and link.

Never silently choose a timezone or contact. Do not switch to calendar.google.com when the connected API permission is missing.
