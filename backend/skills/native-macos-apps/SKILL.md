---
name: native-macos-apps
description: Operate an installed macOS application with fresh visual and accessibility observations. Use for native apps, System Settings, and tasks that require local app UI.
---

# Native macOS workflow

1. Resolve the named installed application with `computer_app`. Do not replace it with a website.
2. Inspect the relevant window read-only, then call `computer_see` immediately before each interaction. Use only the fresh opaque element ID returned for that window.
3. Prefer background accessibility actions. If the observed control has no supported action or explicitly reports a custom-drawn control, retry that same target once using foreground synthetic input.
4. Observe again after every meaningful action and compare the state. If a receipt is stale, discard it and capture a fresh observation rather than retrying the old element.
5. Stop when the requested state is visibly verified. Do not quit, relaunch, close windows, or affect every application unless the user explicitly asks.

If the application is unavailable or accessibility is denied, report that exact blocker. Never claim a click succeeded merely because the tool returned without an error.
