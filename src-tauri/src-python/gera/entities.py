"""Entity loaders — read events, notes, and projects from the filesystem.

All loaders take a ``data_root`` Path and return parsed Pydantic models
ready to be serialized to the frontend via Tauri commands.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel

from gera.frontmatter import parse_frontmatter
from gera.paths import events_file, notes_dir, projects_dir, tasks_file
from gera.renderer import _extract_title

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models (serializable to frontend)
# ---------------------------------------------------------------------------


class EventEntity(BaseModel):
    id: str
    source: str = "local"
    from_: str  # ISO-ish datetime string
    to: str
    name: str
    description: str = ""
    participants: list[str] = []

    class Config:
        # allow `from` as alias since it's a Python keyword
        populate_by_name = True


class TaskEntity(BaseModel):
    text: str
    completed: bool
    raw_line: str
    """Original markdown line (for write-back)."""
    source_file: str
    """Relative path to the file containing this task."""
    line_number: int


class NoteEntity(BaseModel):
    filename: str
    title: str
    body_preview: str
    """First ~100 chars of plain body text."""
    event_ids: list[str] = []
    project_ids: list[str] = []
    raw_content: str
    """Full file content (for rendering / editing)."""


class ProjectEntity(BaseModel):
    id: str
    """Project ID = filename without extension."""
    filename: str
    title: str
    body_preview: str
    event_ids: list[str] = []
    raw_content: str


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_events(data_root: Path) -> list[EventEntity]:
    """Parse ``events.yaml`` and return a list of event entities."""
    path = events_file(data_root)
    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except Exception:
        logger.exception("Failed to parse %s", path)
        return []

    if not isinstance(data, dict) or "events" not in data:
        return []

    events: list[EventEntity] = []
    for entry in data["events"]:
        if not isinstance(entry, dict):
            continue
        try:
            events.append(
                EventEntity(
                    id=str(entry.get("id", "")),
                    source=str(entry.get("source", "local")),
                    from_=str(entry.get("from", "")),
                    to=str(entry.get("to", "")),
                    name=str(entry.get("name", "Untitled")),
                    description=str(entry.get("description", "")),
                    participants=[str(p) for p in entry.get("participants", [])],
                )
            )
        except Exception:
            logger.warning("Skipping malformed event entry: %s", entry)

    return events


def _body_preview(body: str, max_len: int = 100) -> str:
    """First *max_len* characters of body text, stripped of leading headings/whitespace."""
    text = body.lstrip().removeprefix("#").lstrip()
    # Remove the first heading line
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            text = "\n".join(lines[i:])
            break
    return text[:max_len].strip()


def load_notes(data_root: Path) -> list[NoteEntity]:
    """Read all ``.md`` files from ``notes/`` and return note entities."""
    ndir = notes_dir(data_root)
    if not ndir.is_dir():
        return []

    notes: list[NoteEntity] = []
    for md_file in sorted(ndir.glob("**/*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(raw)
            title = _extract_title(body)
            notes.append(
                NoteEntity(
                    filename=md_file.name,
                    title=title,
                    body_preview=_body_preview(body),
                    event_ids=fm.get("event_ids", []) or [],
                    project_ids=fm.get("project_ids", []) or [],
                    raw_content=raw,
                )
            )
        except Exception:
            logger.warning("Failed to read note %s", md_file, exc_info=True)

    return notes


def load_projects(data_root: Path) -> list[ProjectEntity]:
    """Read all ``.md`` files from ``projects/`` and return project entities."""
    pdir = projects_dir(data_root)
    if not pdir.is_dir():
        return []

    projects: list[ProjectEntity] = []
    for md_file in sorted(pdir.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(raw)
            title = _extract_title(body)
            project_id = md_file.stem  # filename without extension
            projects.append(
                ProjectEntity(
                    id=project_id,
                    filename=md_file.name,
                    title=title,
                    body_preview=_body_preview(body),
                    event_ids=fm.get("event_ids", []) or [],
                    raw_content=raw,
                )
            )
        except Exception:
            logger.warning("Failed to read project %s", md_file, exc_info=True)

    return projects


def load_floating_tasks(data_root: Path) -> list[TaskEntity]:
    """Parse ``tasks.md`` for standalone floating tasks."""
    path = tasks_file(data_root)
    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed to read %s", path)
        return []

    tasks: list[TaskEntity] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
            tasks.append(
                TaskEntity(
                    text=stripped[6:],
                    completed=True,
                    raw_line=line,
                    source_file="tasks.md",
                    line_number=i,
                )
            )
        elif stripped.startswith("- [ ] "):
            tasks.append(
                TaskEntity(
                    text=stripped[6:],
                    completed=False,
                    raw_line=line,
                    source_file="tasks.md",
                    line_number=i,
                )
            )

    return tasks
