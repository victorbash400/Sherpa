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


def save_keychain_secret(service: str, secret: str) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("Sherpa account storage currently requires macOS Keychain.")
    result = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            getpass.getuser(),
            "-s",
            service,
            "-w",
            secret,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not save the Google account.")


def delete_keychain_secret(service: str) -> None:
    if sys.platform != "darwin":
        return
    subprocess.run(
        [
            "security",
            "delete-generic-password",
            "-a",
            getpass.getuser(),
            "-s",
            service,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
