import getpass
import os
import subprocess
import sys

KEYCHAIN_SERVICE = "Sherpa Gemini API"


def load_gemini_api_key() -> str | None:
    configured = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if configured:
        return configured
    if sys.platform != "darwin":
        return None
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            getpass.getuser(),
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    key = result.stdout.strip()
    return key or None
