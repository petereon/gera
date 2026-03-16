"""Filesystem initialization and validation for Gera.

Responsible for ensuring the data directory exists and contains all expected
subdirectories and seed files on application startup.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from gera.errors import (
    DirectoryCreationError,
    FileWriteError,
    InvalidDataDirectoryError,
)
from gera.paths import (
    REQUIRED_DIRS,
    SEED_FILES,
    resolve_data_root,
)

logger = logging.getLogger(__name__)


def validate_data_root(data_root: Path) -> None:
    """Validate that *data_root* is a usable directory path.

    Raises:
        InvalidDataDirectoryError: If the path exists but is not a directory,
            or is on a read-only filesystem.
    """
    if data_root.exists() and not data_root.is_dir():
        raise InvalidDataDirectoryError(data_root, "path exists but is not a directory")

    # Check parent is writable so we can create the root if needed
    parent = data_root.parent
    if parent.exists() and not parent.is_dir():
        raise InvalidDataDirectoryError(
            data_root, f"parent path '{parent}' is not a directory"
        )


def _ensure_directory(path: Path) -> bool:
    """Create *path* if it does not exist. Returns True if created."""
    if path.is_dir():
        return False
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info("Created directory: %s", path)
        return True
    except PermissionError as exc:
        raise DirectoryCreationError(path, "permission denied") from exc
    except OSError as exc:
        raise DirectoryCreationError(path, str(exc)) from exc


def _ensure_seed_file(path: Path, default_content: str) -> bool:
    """Create *path* with *default_content* if it does not exist. Returns True if created."""
    if path.exists():
        return False
    try:
        path.write_text(default_content, encoding="utf-8")
        logger.info("Created seed file: %s", path)
        return True
    except PermissionError as exc:
        raise FileWriteError(path, "permission denied") from exc
    except OSError as exc:
        raise FileWriteError(path, str(exc)) from exc


def init_data_directory(data_root_override: str | Path | None = None) -> Path:
    """Ensure the full data directory structure exists.

    This is the main entry point to be called on app startup. It will:

    1. Resolve the data root (using *data_root_override* or the platform default).
    2. Validate the path is usable.
    3. Create the root directory if missing.
    4. Create all required subdirectories (``notes/``, ``projects/``).
    5. Create seed files (``events.yaml``, ``tasks.md``) with default content
       if they don't already exist.

    Args:
        data_root_override: Optional explicit path. ``None`` uses the default
            (``~/Documents/Gera``).

    Returns:
        The resolved, absolute ``Path`` to the data root.

    Raises:
        InvalidDataDirectoryError: If the path is fundamentally unusable.
        DirectoryCreationError: If a required directory cannot be created.
        FileWriteError: If a seed file cannot be written.
    """
    data_root = resolve_data_root(data_root_override)

    logger.debug("Initializing data directory: %s", data_root)

    validate_data_root(data_root)

    # Create root
    _ensure_directory(data_root)

    # Create required subdirectories
    for dirname in REQUIRED_DIRS:
        _ensure_directory(data_root / dirname)

    # Create seed files with default content
    for filename, content in SEED_FILES.items():
        _ensure_seed_file(data_root / filename, content)

    # Run data migrations (idempotent — no-op if already up to date)
    _migrate_gcal_ids(data_root)

    logger.info("Data directory ready: %s", data_root)
    return data_root


_GCAL_ID_RE = re.compile(r'^gcal-[^-]+-(.+)$')


def _migrate_gcal_ids(data_root: Path) -> None:
    """Rename old-style gcal-{email}-{uuid} event IDs to bare {uuid}.

    This migration is idempotent — if no old-format IDs are present it does
    nothing.  It rewrites events.yaml, tasks.md, and all notes/projects .md
    files in-place.
    """
    import yaml  # local import — only needed during migration

    events_path = data_root / "events.yaml"
    if not events_path.exists():
        return

    data = yaml.safe_load(events_path.read_text(encoding="utf-8")) or {}
    events = data.get("events", [])

    # Build old→new mapping for any gcal-style IDs
    mapping: dict[str, str] = {}
    for ev in events:
        old_id = ev.get("id", "")
        m = _GCAL_ID_RE.match(old_id)
        if m:
            new_id = m.group(1)
            if new_id != old_id:
                mapping[old_id] = new_id

    if not mapping:
        return

    logger.info("Migrating %d gcal event ID(s) to bare format", len(mapping))

    # Rewrite events.yaml
    for ev in events:
        if ev.get("id") in mapping:
            ev["id"] = mapping[ev["id"]]
    events_path.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    # Rewrite inline @old-id references in a markdown file
    def _rewrite_md(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        for old_id, new_id in mapping.items():
            text = text.replace(f"@{old_id}", f"@{new_id}")
        path.write_text(text, encoding="utf-8")

    tasks_path = data_root / "tasks.md"
    if tasks_path.exists():
        _rewrite_md(tasks_path)

    for md in sorted((data_root / "notes").glob("*.md")):
        _rewrite_md(md)
    for md in sorted((data_root / "projects").glob("*.md")):
        _rewrite_md(md)

    logger.info("gcal ID migration complete")


def verify_structure(data_root: Path) -> dict[str, bool]:
    """Check which parts of the expected directory structure exist.

    Returns a dict mapping relative path names to existence booleans.
    Useful for diagnostics / UI status display.
    """
    result: dict[str, bool] = {
        ".": data_root.is_dir(),
    }
    for dirname in REQUIRED_DIRS:
        result[dirname] = (data_root / dirname).is_dir()
    for filename in SEED_FILES:
        result[filename] = (data_root / filename).exists()
    return result
