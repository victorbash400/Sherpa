import asyncio
import base64
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from backend.credential_store import (
    delete_keychain_secret,
    load_keychain_secret,
    save_keychain_secret,
)


GoogleConnection = Literal["workspace", "cloud"]
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_REDIRECT_URI = "http://127.0.0.1:8000/oauth/google/callback"
KEYCHAIN_SERVICES = {
    "workspace": "Sherpa Google Workspace",
    "cloud": "Sherpa Google Cloud",
}
SCOPES = {
    "workspace": (
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/presentations.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.events.freebusy",
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/directory.readonly",
        "https://www.googleapis.com/auth/cloud-platform",
    ),
    "cloud": (
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/cloud-platform",
    ),
}


class GoogleAuthManager:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, str]] = {}
        self._records = {
            connection: self._load(connection)
            for connection in KEYCHAIN_SERVICES
        }
        self._lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def client_id(self) -> str | None:
        return os.getenv("SHERPA_GOOGLE_CLIENT_ID")

    @property
    def client_secret(self) -> str | None:
        return os.getenv("SHERPA_GOOGLE_CLIENT_SECRET")

    def snapshot(self, connection: GoogleConnection) -> dict[str, Any]:
        record = self._records.get(connection)
        return {
            "configured": self.configured,
            "connected": bool(record and record.get("refresh_token")),
            "email": record.get("email") if record else None,
            "name": record.get("name") if record else None,
            "picture": record.get("picture") if record else None,
        }

    def begin(self, connection: GoogleConnection) -> str:
        if not self.configured:
            raise RuntimeError(
                "Sherpa's Google OAuth client is not configured. Set "
                "SHERPA_GOOGLE_CLIENT_ID and SHERPA_GOOGLE_CLIENT_SECRET."
            )
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        self._states[state] = {
            "connection": connection,
            "verifier": verifier,
        }
        return GOOGLE_AUTH_URL + "?" + urlencode({
            "client_id": self.client_id,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES[connection]),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })

    async def finish(self, state: str, code: str) -> GoogleConnection:
        pending = self._states.pop(state, None)
        if not pending:
            raise ValueError("The Google connection request expired or is invalid.")
        connection = pending["connection"]
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "code_verifier": pending["verifier"],
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            })
            token_response.raise_for_status()
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            if not access_token or not refresh_token:
                raise RuntimeError("Google did not return an offline account token.")
            user_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_response.raise_for_status()
            user = user_response.json()
            if connection == "workspace":
                await validate_workspace_token(client, access_token)
        record = {
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "picture": user.get("picture", ""),
            "refresh_token": refresh_token,
            "access_token": access_token,
            "expires_at": (
                datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
            ).isoformat(),
            "scope": tokens.get("scope", ""),
        }
        self._records[connection] = record
        save_keychain_secret(KEYCHAIN_SERVICES[connection], json.dumps(record))
        return connection  # type: ignore[return-value]

    async def access_token(self, connection: GoogleConnection) -> str | None:
        async with self._lock:
            record = self._records.get(connection)
            if not record or not record.get("refresh_token"):
                return None
            expires_at = datetime.fromisoformat(record["expires_at"])
            if expires_at > datetime.now(UTC) + timedelta(minutes=2):
                return record.get("access_token")
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(GOOGLE_TOKEN_URL, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": record["refresh_token"],
                    "grant_type": "refresh_token",
                })
                response.raise_for_status()
                tokens = response.json()
            record["access_token"] = tokens["access_token"]
            record["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
            ).isoformat()
            save_keychain_secret(KEYCHAIN_SERVICES[connection], json.dumps(record))
            return record["access_token"]

    def disconnect(self, connection: GoogleConnection) -> None:
        self._records[connection] = None
        delete_keychain_secret(KEYCHAIN_SERVICES[connection])

    def _load(self, connection: GoogleConnection) -> dict[str, Any] | None:
        value = load_keychain_secret(KEYCHAIN_SERVICES[connection])
        if not value:
            return None
        try:
            record = json.loads(value)
        except json.JSONDecodeError:
            return None
        return record if isinstance(record, dict) else None


google_auth = GoogleAuthManager()


async def validate_workspace_token(client: httpx.AsyncClient, access_token: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    checks = (
        ("Gmail", "https://gmail.googleapis.com/gmail/v1/users/me/profile"),
        (
            "Google Drive",
            "https://www.googleapis.com/drive/v3/files?pageSize=1&fields=files(id)",
        ),
    )
    for product, url in checks:
        response = await client.get(url, headers=headers)
        if response.is_success:
            continue
        try:
            detail = response.json().get("error", {}).get("message")
        except ValueError:
            detail = response.text[:300]
        raise RuntimeError(
            f"{product} authorization failed: {detail or response.reason_phrase}. "
            "Reconnect Google Workspace and approve the requested access."
        )
