from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def inspect_local_artifacts(
    directory: str,
    name_contains: str = "",
    suffix: str = "",
) -> dict[str, Any]:
    """Inspect matching files in one local directory without opening an app.

    Use this after a browser or macOS application creates or downloads a file.
    The result verifies only files that currently exist on disk.

    Args:
        directory: Absolute directory to inspect, such as /Users/name/Downloads.
        name_contains: Optional case-insensitive text that must occur in the filename.
        suffix: Optional filename suffix such as .xlsx or .pdf.
    """
    root = Path(directory).expanduser()
    if not root.is_absolute():
        return {
            "status": "failed",
            "outcome": "The directory was not inspected because it is not an absolute path.",
        }
    if not root.exists():
        return {
            "status": "not_found",
            "directory": str(root),
            "outcome": "The directory does not exist.",
            "files": [],
        }
    if not root.is_dir():
        return {
            "status": "failed",
            "directory": str(root),
            "outcome": "The supplied path exists but is not a directory.",
        }

    needle = name_contains.casefold().strip()
    wanted_suffix = suffix.casefold().strip()
    files = []
    try:
        entries = root.iterdir()
        for entry in entries:
            if not entry.is_file():
                continue
            filename = entry.name
            if needle and needle not in filename.casefold():
                continue
            if wanted_suffix and not filename.casefold().endswith(wanted_suffix):
                continue
            stat = entry.stat()
            files.append({
                "name": filename,
                "path": str(entry.resolve()),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=UTC,
                ).isoformat(),
            })
    except OSError as error:
        return {
            "status": "failed",
            "directory": str(root),
            "outcome": f"The directory could not be inspected: {error}",
        }

    files.sort(key=lambda item: item["modified_at"], reverse=True)
    return {
        "status": "found" if files else "not_found",
        "directory": str(root),
        "outcome": (
            f"Found {len(files)} matching local file(s)."
            if files
            else "No matching local files currently exist."
        ),
        "files": files,
    }
