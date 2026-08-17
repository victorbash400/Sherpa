import tempfile
import unittest
from pathlib import Path

from backend.tools.local_artifacts import inspect_local_artifacts


class LocalArtifactTests(unittest.TestCase):
    def test_returns_exact_matching_file_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "Report.xlsx"
            expected.write_bytes(b"workbook")
            (Path(directory) / "Report.pdf").write_bytes(b"pdf")

            result = inspect_local_artifacts(directory, "report", ".xlsx")

            self.assertEqual(result["status"], "found")
            self.assertEqual(result["files"][0]["path"], str(expected.resolve()))
            self.assertEqual(result["files"][0]["size_bytes"], 8)

    def test_reports_absent_file_without_claiming_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = inspect_local_artifacts(directory, "missing", ".xlsx")

            self.assertEqual(result["status"], "not_found")
            self.assertEqual(result["files"], [])

    def test_rejects_relative_directory(self) -> None:
        result = inspect_local_artifacts("Downloads", "report", ".xlsx")

        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
