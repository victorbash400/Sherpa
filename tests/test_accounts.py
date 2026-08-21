import tempfile
import unittest
from pathlib import Path

from backend.accounts import AccountStore, DEMO_EMAIL, DEMO_PASSWORD


class AccountStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.directory.name) / "accounts.sqlite3")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_create_authenticate_resume_and_logout(self) -> None:
        created = self.store.create("Person@Example.com", "password1", "Person")
        authenticated = self.store.authenticate("person@example.com", "password1")

        self.assertIsNotNone(authenticated)
        account, token = authenticated or (None, "")
        self.assertEqual(account, created)
        self.assertEqual(self.store.resume(token), created)

        self.store.logout(token)
        self.assertIsNone(self.store.resume(token))

    def test_account_passwords_and_sessions_are_isolated(self) -> None:
        first = self.store.create("first@example.com", "password1", "First")
        second = self.store.create("second@example.com", "password2", "Second")

        first_login = self.store.authenticate(first.email, "password1")
        second_login = self.store.authenticate(second.email, "password2")

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.store.resume(first_login[1]).id, first.id)  # type: ignore[index,union-attr]
        self.assertEqual(self.store.resume(second_login[1]).id, second.id)  # type: ignore[index,union-attr]
        self.assertIsNone(self.store.authenticate(first.email, "password2"))

    def test_rejects_duplicate_email(self) -> None:
        self.store.create("person@example.com", "password1", "Person")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.store.create("PERSON@example.com", "password2", "Other")

    def test_demo_account_is_created_on_first_sign_in(self) -> None:
        authenticated = self.store.authenticate(DEMO_EMAIL, DEMO_PASSWORD)

        self.assertIsNotNone(authenticated)
        account, _ = authenticated or (None, "")
        self.assertEqual(account.email, DEMO_EMAIL)  # type: ignore[union-attr]
        self.assertEqual(account.name, "Demo")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
