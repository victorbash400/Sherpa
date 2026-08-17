# Peekaboo Sherpa

Peekaboo Sherpa is Sherpa's maintained fork of
[Peekaboo](https://github.com/openclaw/Peekaboo). It provides the native macOS
observation and interaction runtime used by Sherpa's Gemini agents.

This fork remains a general macOS CLI and MCP server. Gemini planning, task
orchestration, voice interaction, and tool policy live in the surrounding
Sherpa application; they are not embedded into the Peekaboo runtime.

## Why this fork exists

Sherpa needs computer-use tools that can operate native applications while
keeping tool results explicit and machine-verifiable. This fork adapts Peekaboo
for that workflow with:

- structured Accessibility inspection without requiring screenshots;
- process- and window-bound element receipts;
- background application targeting where macOS supports it;
- explicit foreground synthetic input for custom-drawn controls;
- compound file-dialog handling with verified outcomes;
- fail-fast handling for non-actionable and stale targets;
- MCP responses designed for Sherpa's Gemini tool loop.

The goal is not to hide failures from the model. An interaction that cannot be
confirmed returns a visible error so Sherpa can observe the current state and
choose a safe next action.

## Sherpa integration

Sherpa starts the in-repository release binary from:

```text
peekaboo-sherpa/Apps/CLI/.build/release/peekaboo
```

The Python integration is defined in:

```text
backend/tools/computer_use/peekaboo.py
```

The exposed MCP tools cover application and window discovery, structured UI
inspection, clicks, typing, keyboard input, scrolling, dialogs, menus, and
other native macOS operations. Screenshots are currently disabled in Sherpa's
agent tool policy.

## Build

Requirements:

- macOS 15 or later
- Swift 6.2 or later
- Node.js 22 or later for JavaScript workspace tooling
- repository submodules initialized

From this directory, build the binary Sherpa uses:

```sh
swift build --configuration release --package-path Apps/CLI
```

Run the focused Swift packages directly when changing the fork:

```sh
swift test --package-path Core/PeekabooAutomationKit
swift test --package-path Core/PeekabooCore
```

The upstream development commands remain available:

```sh
pnpm install --frozen-lockfile
pnpm run lint:docs
pnpm run test:safe
```

Do not install the upstream Homebrew or npm release when testing Sherpa. Those
packages do not contain the changes maintained in this directory.

## Runtime principles

1. Observe the relevant application or window before interacting with it.
2. Carry the capture-time process and window identity into the action.
3. Prefer background Accessibility actions when the target advertises support.
4. Use foreground synthetic input only for controls that require physical input.
5. Verify the resulting application state before reporting completion.
6. Fail explicitly when the target changed or the outcome is uncertain.

## Upstream documentation

Peekaboo's original command and architecture documentation is retained in this
directory and remains the reference for the underlying runtime:

- [Architecture](docs/ARCHITECTURE.md)
- [Automation](docs/automation.md)
- [MCP](docs/MCP.md)
- [Command reference](docs/commands/README.md)
- [Building from source](docs/building.md)
- [Testing](docs/testing/tools.md)

Upstream source and releases are available from
[openclaw/Peekaboo](https://github.com/openclaw/Peekaboo). Peekaboo Sherpa is a
Sherpa-maintained fork and is not presented as an official OpenClaw release.

## License and attribution

Peekaboo Sherpa retains Peekaboo's MIT license and original copyright notice.
See [LICENSE](LICENSE).
