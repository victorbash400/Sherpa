---
name: workspace-email
description: Search, read, draft, and send Gmail messages through the connected Google Workspace account. Use for email discovery, extracting details from threads, composing replies, or delivering email.
---

# Gmail workflow

1. Use `workspace_gmail_search_threads` with narrow Gmail syntax. Begin with sender, subject, date, or exact phrases from the request; widen only when no result matches.
2. Compare subjects, senders, and dates. Open the best candidate with `workspace_gmail_get_thread` before relying on its contents. Do not infer details from snippets alone.
3. Preserve names, dates, amounts, links, and instructions exactly when passing email facts into another tool or skill.
4. Reply with `workspace_gmail_reply` so the message stays in the original thread. Use reply-all only when the user asks or every existing recipient clearly belongs in the response. Use `workspace_gmail_forward` when the original content and attachments must go to new recipients.
5. For a draft, use `workspace_gmail_create_draft` or `workspace_gmail_create_rich_draft` when HTML or attachments are needed. For an explicit request to send, use `workspace_gmail_send_message`; use `workspace_gmail_send_rich_message` only when HTML or attachments are required. Verify all recipients, subject, body, and attachment names before sending.
6. Use `workspace_gmail_modify_message` for labels and mailbox state: remove `UNREAD` to mark read, add `UNREAD` to mark unread, remove `INBOX` to archive, and add or remove `STARRED` for stars. Use the trash tool only for an explicit request.
7. Report the returned draft, message, or thread ID as evidence. Never claim delivery from a compose step alone.

If Gmail access is unavailable, name the missing Gmail connection or permission once. Do not open Gmail in Chrome as a silent substitute.

Example: “Find the latest Devpost prize email and send the details to Pat” means search, open the latest credible thread, extract exact prize details, resolve Pat's address if supplied by another selected skill, then send and report the message ID.
