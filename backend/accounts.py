from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator
from uuid import uuid4

from backend.account_context import APPLICATION_DIRECTORY, ActiveAccount


DATABASE_PATH = APPLICATION_DIRECTORY / "accounts.sqlite3"
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DEMO_EMAIL = "demo@sherpa.local"
DEMO_PASSWORD = "sherpa-demo"
DEMO_NAME = "Demo"


@dataclass(frozen=True)
class StoredAccount:
    id: str
    email: str
    name: str
    password_hash: str
    salt: str


class AccountStore:
    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );
                """
            )

    def create(self, email_input: str, password: str, name_input: str) -> ActiveAccount:
        email = email_input.strip().lower()
        name = name_input.strip()
        self._validate(email, password, name)
        salt = os.urandom(16).hex()
        account = StoredAccount(
            id=str(uuid4()),
            email=email,
            name=name,
            password_hash=self._hash_password(password, salt),
            salt=salt,
        )
        try:
            with self._connection() as connection:
                connection.execute(
                    "INSERT INTO accounts (id, email, name, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
                    (account.id, account.email, account.name, account.password_hash, account.salt),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("An account with this email already exists.") from error
        return self._public(account)

    def authenticate(self, email_input: str, password: str) -> tuple[ActiveAccount, str] | None:
        email = email_input.strip().lower()
        if email == DEMO_EMAIL:
            self._ensure_demo_account()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, email, name, password_hash, salt FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
        if not row:
            return None
        account = StoredAccount(**dict(row))
        if not hmac.compare_digest(
            self._hash_password(password, account.salt),
            account.password_hash,
        ):
            return None
        return self._public(account), self._create_session(account.id)

    def _ensure_demo_account(self) -> None:
        with self._connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM accounts WHERE email = ?",
                (DEMO_EMAIL,),
            ).fetchone()
        if exists:
            return
        try:
            self.create(DEMO_EMAIL, DEMO_PASSWORD, DEMO_NAME)
        except ValueError:
            pass

    def resume(self, token: str) -> ActiveAccount | None:
        if not token:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT accounts.id, accounts.email, accounts.name
                FROM sessions JOIN accounts ON accounts.id = sessions.account_id
                WHERE sessions.token_hash = ?
                """,
                (self._token_hash(token),),
            ).fetchone()
        return ActiveAccount(**dict(row)) if row else None

    def logout(self, token: str) -> None:
        if not token:
            return
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (self._token_hash(token),),
            )

    def _create_session(self, account_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, account_id) VALUES (?, ?)",
                (self._token_hash(token), account_id),
            )
        return token

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=16384,
            r=8,
            p=1,
            dklen=64,
        ).hex()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _validate(email: str, password: str, name: str) -> None:
        if not EMAIL.fullmatch(email):
            raise ValueError("Enter a valid email address.")
        if not name or len(name) > 80:
            raise ValueError("Enter a name under 80 characters.")
        if len(password) < 8 or len(password) > 128:
            raise ValueError("Password must be 8 to 128 characters.")

    @staticmethod
    def _public(account: StoredAccount) -> ActiveAccount:
        return ActiveAccount(id=account.id, email=account.email, name=account.name)


account_store = AccountStore()
