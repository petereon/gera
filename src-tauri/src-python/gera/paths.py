"""Path constants and utilities for the Gera data directory.

The default data directory layout:

    <data_root>/
    ├── events.yaml       # Calendar event definitions (YAML)
    ├── tasks.md          # Floating tasks not associated with anything
    ├── notes/            # Markdown note files (Floating/Inbox)
    └── projects/         # Markdown project files (ID = filename)
"""

from pathlib import Path


# --- Directory / file names (relative to data root) ---

EVENTS_FILE = "events.yaml"
TASKS_FILE = "tasks.md"
NOTES_DIR = "notes"
PROJECTS_DIR = "projects"

# All subdirectories that must exist
REQUIRED_DIRS: tuple[str, ...] = (NOTES_DIR, PROJECTS_DIR)

# All seed files that should be created if missing
SEED_FILES: dict[str, str] = {
    EVENTS_FILE: "events: []\n",
    TASKS_FILE: "# Tasks\n",
}


def default_data_root() -> Path:
    """Return the platform-appropriate default data root for Gera.

    - macOS:   ~/Documents/Gera
    - Linux:   ~/Documents/Gera
    - Windows: ~/Documents/Gera
    """
    return Path.home() / "Documents" / "Gera"


def resolve_data_root(override: str | Path | None = None) -> Path:
    """Resolve the data root directory.

    Args:
        override: An explicit path to use instead of the default.
                  Supports ``~`` expansion.

    Returns:
        Absolute, expanded ``Path`` to the data root directory.
    """
    if override is not None:
        return Path(override).expanduser().resolve()
    return default_data_root().resolve()


# --- Convenience path builders ---


def events_file(data_root: Path) -> Path:
    """Absolute path to the events YAML file."""
    return data_root / EVENTS_FILE


def tasks_file(data_root: Path) -> Path:
    """Absolute path to the floating tasks Markdown file."""
    return data_root / TASKS_FILE


def notes_dir(data_root: Path) -> Path:
    """Absolute path to the notes directory."""
    return data_root / NOTES_DIR


def projects_dir(data_root: Path) -> Path:
    """Absolute path to the projects directory."""
    return data_root / PROJECTS_DIR


def note_file(data_root: Path, name: str) -> Path:
    """Absolute path to a specific note file.

    Args:
        data_root: The data root directory.
        name: Note filename (with or without ``.md`` extension).
    """
    if not name.endswith(".md"):
        name = f"{name}.md"
    return notes_dir(data_root) / name


def project_file(data_root: Path, name: str) -> Path:
    """Absolute path to a specific project file.

    Args:
        data_root: The data root directory.
        name: Project filename (with or without ``.md`` extension).
    """
    if not name.endswith(".md"):
        name = f"{name}.md"
    return projects_dir(data_root) / name
