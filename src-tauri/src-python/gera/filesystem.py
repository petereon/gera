"""Filesystem initialization and validation for Gera.

Responsible for ensuring the data directory exists and contains all expected
subdirectories and seed files on application startup.
"""

from __future__ import annotations

import logging
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

    logger.info("Data directory ready: %s", data_root)
    return data_root


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
