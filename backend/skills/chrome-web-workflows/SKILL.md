---
name: chrome-web-workflows
description: Navigate and operate the user's connected Chrome tabs with accessibility snapshots and verification. Use for explicit websites, existing browser sessions, and web-only workflows.
---

# Chrome workflow

1. Begin with `browser_tabs`; reuse the relevant existing tab when possible. Use `browser_snapshot` before acting, or `browser_find` for one target in a large page.
2. Act on exact references from the current snapshot and include a concise human-readable element label.
3. After navigation, typing, selection, or submission, capture a new snapshot and verify the expected page state.
4. Keep work inside the user's connected Chrome. If the extension is disconnected, report it and stop.
5. Do not use a website as a substitute when the user named an installed app or when a selected API skill supports the work. Use Chrome only for an explicitly requested web surface or a genuinely web-only capability.

For forms, fill stable fields first, review values, and submit only when the user's request authorizes the consequential action.
