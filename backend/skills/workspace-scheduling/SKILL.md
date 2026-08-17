---
name: workspace-scheduling
description: Resolve Google contacts and inspect, create, update, or delete Google Calendar events. Use for scheduling, conflict checks, attendee resolution, and calendar changes.
---

# Calendar and contacts workflow

1. Resolve named people with `workspace_people_search_contacts` when an address is not already explicit. Do not guess between multiple matches.
2. Use `workspace_calendar_find_free_time` for availability and `workspace_calendar_list_events` for event context. Do not infer availability from titles alone.
3. Read a specific event with `workspace_calendar_get_event` before reporting its guests, attachments, location, joining details, or Meet link.
4. Create with `workspace_calendar_create_event` only after title, start, end, timezone, and attendees are unambiguous. Request a Meet link when the user asks for an online meeting.
5. Update, respond to, or delete only a verified event ID. Treat deletion and invitations as consequential actions; confirm uncertain targets first.
6. Re-read the result and report the event ID, Calendar link, and Meet link when present.

Never silently choose a timezone or contact. Do not switch to calendar.google.com when the connected API permission is missing.
