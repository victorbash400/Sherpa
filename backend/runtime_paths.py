from __future__ import annotations

import os
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def resource_root() -> Path:
    configured = os.getenv("SHERPA_RESOURCE_ROOT")
    return Path(configured) if configured else SOURCE_ROOT


def peekaboo_binary() -> Path:
    configured = os.getenv("SHERPA_PEEKABOO_BINARY")
    if configured:
        return Path(configured)
    packaged = resource_root() / "peekaboo"
    if packaged.is_file():
        return packaged
    return SOURCE_ROOT / "peekaboo-sherpa/Apps/CLI/.build/release/peekaboo"


def playwright_mcp_binary() -> Path:
    return resource_root() / "node_modules/.bin/playwright-mcp"
