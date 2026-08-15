import getpass
import os
import subprocess
import sys

GEMINI_KEYCHAIN_SERVICE = "Sherpa Gemini API"
PLAYWRIGHT_KEYCHAIN_SERVICE = "Sherpa Playwright MCP"


def load_gemini_api_key() -> str | None:
    configured = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if configured:
        return configured
    return load_keychain_secret(GEMINI_KEYCHAIN_SERVICE)


def load_playwright_extension_token() -> str | None:
    configured = os.getenv("PLAYWRIGHT_MCP_EXTENSION_TOKEN")
    if configured:
        return configured
    return load_keychain_secret(PLAYWRIGHT_KEYCHAIN_SERVICE)


def load_keychain_secret(service: str) -> str | None:
    if sys.platform != "darwin":
        return None
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            getpass.getuser(),
            "-s",
            service,
            "-w",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    key = result.stdout.strip()
    return key or None
