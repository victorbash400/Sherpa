---
name: native-whatsapp
description: Operate WhatsApp through the installed macOS application. Use whenever the user asks to open, inspect, read, search, or send something using WhatsApp and does not explicitly request WhatsApp Web.
---

# Native WhatsApp

- Use computer tools with the installed WhatsApp application.
- Never navigate to WhatsApp Web unless the user explicitly says to use the web version.
- Locate or launch WhatsApp with `computer_app`, then observe its window before interacting.
- Use a fresh `computer_see` result immediately before every click or text action.
- Search for the requested contact or conversation, verify the visible recipient, then compose the message.
- To attach an existing local file, open WhatsApp's attachment picker, then call `computer_dialog` once with `action=file`, the exact absolute `path`, `app=WhatsApp`, `select=default`, and `foreground=true`. Do not inspect or click through the file picker manually.
- Treat sending as a consequential action: verify the recipient and message before the final send interaction.
- If the native application is unavailable or disabled, report that exact problem. Do not silently substitute a website.
