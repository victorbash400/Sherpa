import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.connections import APPLICATION_ROOTS, application_metadata
from backend.permission_store import PermissionStore


class AppPermissionTests(unittest.TestCase):
    def permission_store(self) -> PermissionStore:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        permission_file = Path(temporary_directory.name) / "permissions.json"
        with patch("backend.permission_store.PERMISSION_FILE", permission_file):
            return PermissionStore()

    def test_app_names_ignore_invisible_formatting_characters(self) -> None:
        store = self.permission_store()
        store.register_apps([{"name": "WhatsApp", "bundle_id": "net.whatsapp.WhatsApp"}])

        self.assertTrue(store.app_enabled("\u200eWhatsApp"))

    def test_pid_targets_resolve_to_bundle_permissions(self) -> None:
        store = self.permission_store()
        store.register_apps([{"name": "WhatsApp", "bundle_id": "net.whatsapp.WhatsApp"}])

        with patch("backend.permission_store.bundle_id_for_pid", return_value="net.whatsapp.WhatsApp"):
            self.assertTrue(store.app_enabled("PID:25681"))

    def test_pid_targets_with_window_titles_resolve_to_bundle_permissions(self) -> None:
        store = self.permission_store()
        store.register_apps([{"name": "WhatsApp", "bundle_id": "net.whatsapp.WhatsApp"}])

        with patch("backend.permission_store.bundle_id_for_pid", return_value="net.whatsapp.WhatsApp"):
            self.assertTrue(store.app_enabled("PID:25681:Open"))

    def test_finder_installation_location_is_discovered(self) -> None:
        finder_root = Path("/System/Library/CoreServices")

        self.assertIn(finder_root, APPLICATION_ROOTS)
        metadata = application_metadata(finder_root / "Finder.app")
        self.assertEqual(metadata and metadata["bundle_id"], "com.apple.finder")


if __name__ == "__main__":
    unittest.main()
