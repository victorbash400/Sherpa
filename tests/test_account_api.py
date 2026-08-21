import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.account_context import account_context
from backend.accounts import AccountStore
from backend.main import app


class AccountApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.directory.name) / "accounts.sqlite3")
        self.store_patch = patch("backend.main.account_store", self.store)
        self.store_patch.start()
        account_context.clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        account_context.clear()
        self.store_patch.stop()
        self.directory.cleanup()

    def test_account_flow_and_signed_out_gate(self) -> None:
        self.assertEqual(self.client.get("/connections").status_code, 401)

        created = self.client.post("/accounts", json={
            "email": "person@example.com",
            "password": "password1",
            "name": "Person",
        })
        self.assertEqual(created.status_code, 201)

        signed_in = self.client.post("/accounts/authenticate", json={
            "email": "person@example.com",
            "password": "password1",
        })
        self.assertEqual(signed_in.status_code, 200)
        token = signed_in.json()["token"]
        self.assertEqual(account_context.require().email, "person@example.com")

        account_context.clear()
        resumed = self.client.post("/accounts/session", json={"token": token})
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.json()["name"], "Person")

        signed_out = self.client.post("/accounts/logout", json={"token": token})
        self.assertEqual(signed_out.status_code, 200)
        self.assertIsNone(account_context.current())
        self.assertEqual(
            self.client.post("/accounts/session", json={"token": token}).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
