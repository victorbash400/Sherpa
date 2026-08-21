from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock


APPLICATION_DIRECTORY = Path.home() / "Library" / "Application Support" / "Sherpa"


@dataclass(frozen=True)
class ActiveAccount:
    id: str
    email: str
    name: str


class AccountContext:
    def __init__(self) -> None:
        self._account: ActiveAccount | None = None
        self._lock = RLock()

    def activate(self, account: ActiveAccount) -> None:
        with self._lock:
            self._account = account
            self.profile_directory().mkdir(parents=True, exist_ok=True)

    def clear(self) -> None:
        with self._lock:
            self._account = None

    def current(self) -> ActiveAccount | None:
        with self._lock:
            return self._account

    def require(self) -> ActiveAccount:
        account = self.current()
        if not account:
            raise RuntimeError("Sign in to Sherpa first.")
        return account

    def profile_directory(self) -> Path:
        account = self.current()
        profile_id = account.id if account else "signed-out"
        return APPLICATION_DIRECTORY / "profiles" / profile_id


account_context = AccountContext()
