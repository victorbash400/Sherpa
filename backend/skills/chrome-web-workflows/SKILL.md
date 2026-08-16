---
name: chrome-web-workflows
description: Navigate and operate connected Chrome tabs, including efficient repetitive DOM edits, with targeted reads and verification. Use for explicit websites, existing browser sessions, and web-only workflows.
---

# Chrome workflow

1. Begin with `browser_tabs`; reuse the relevant existing tab when possible. Use `browser_snapshot` before acting, or `browser_find` for one target in a large page.
2. Act on exact references from the current snapshot and include a concise human-readable element label.
3. If a stable DOM-backed edit would otherwise take many click/type cycles, use one short `browser_evaluate` function to apply the repetitive transformation. Return a concise count or result. Do not use it for canvas-only editors, authentication, permissions, navigation, sending, publishing, deletion, purchase, upload, or form submission.
4. After a programmatic edit, navigation, typing, selection, or submission, use `browser_find` or a relevant snapshot to verify the expected visible state. Do not alternate full snapshots with every keystroke.
5. Keep work inside the user's connected Chrome. If the extension is disconnected, report it and stop.
6. Do not use a website as a substitute when the user named an installed app or when a selected API skill supports the work. Use Chrome only for an explicitly requested web surface or a genuinely web-only capability.

For forms, fill stable fields first, review values, and submit only when the user's request authorizes the consequential action.
