"""In-memory SQLite repository for Gera entities.

Maintains a shared in-memory database that mirrors the on-disk state.
A keep-alive connection is held open for the lifetime of the process
to prevent SQLite from deallocating the shared memory segment.

Usage::

    repo = Repository(data_root)
    repo.reload()                 # initial load from disk
    events = repo.list_events()   # query
    repo.reload()                 # call again after fs-changed
    repo.close()                  # on shutdown
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from gera.entities import EventEntity, EventMetadata, NoteEntity, ProjectEntity, TaskEntity, TimeReference
from gera.frontmatter import parse_frontmatter, serialize_frontmatter
from gera.paths import (
    events_file,
    note_file,
    notes_dir,
    project_file,
    projects_dir,
    tasks_file,
)
from gera.renderer import extract_title
from gera.utils import body_preview

logger = logging.getLogger(__name__)


def _sanitize_content(content: str) -> str:
    """Remove HTML-encoded spaces and strip trailing whitespace from every line.

    MDXEditor (and other HTML-aware editors) can produce ``&#x20;`` entities
    at the end of lines.  These must never reach the on-disk markdown files.
    """
    # Replace HTML space entity with a literal space first so mid-line
    # occurrences become readable text rather than disappearing.
    content = content.replace("&#x20;", " ")
    # Strip any trailing spaces/tabs from every line.
    content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
    return content


_DB_URI = "file::memory:?cache=shared"

DATA_CHANGED_EVENT = "gera://data-changed"

# Type alias for the emit callback
EmitFn = Callable[[str, str], None]

# ---------------------------------------------------------------------------
# Task-line parsing patterns (moved from service/tasks.py)
# ---------------------------------------------------------------------------

# Matches a markdown task checkbox line: - [ ] or - [x]
_TASK_PAT = re.compile(r"^[-*+] \[([ xX])\] (.+)")

# Matches time/event references inside task text:
#   @2026-02-20T09:00            → absolute datetime
#   @before[30m]:standup-feb-20  → relative offset to an event
#   @event-id                    → plain event reference
_TIME_PAT = re.compile(
    r"@(?:"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})"  # group 1: absolute datetime
    r"|(\w+?)\[(\d+)([YMWdhm])\]:([\w\-:]+)"  # groups 2-5: modifier[offset]:target
    r"|([\w\-]+)"  # group 6: plain @event-id
    r")"
)

# Matches #project-id references
_PROJECT_PAT = re.compile(r"#([\w\-]+)")

# SQL for inserting task rows
_TASKS_INSERT_SQL = (
    "INSERT INTO tasks (text, completed, raw_line, source_file, line_number, "
    "deadline, event_ids, project_ids, time_references, "
    "resolved_event_names, resolved_project_names) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _parse_datetime(value: object) -> datetime:
    """Coerce a YAML value (datetime or str) to a ``datetime``."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class Repository:
    """Shared in-memory SQLite store for all Gera entities."""

    def __init__(self, data_root: Path) -> None:
        self._data_root = data_root
        self._emit_fn: EmitFn | None = None

        # Keep-alive connection — must stay open for the database to survive
        self._keep_alive: sqlite3.Connection = sqlite3.connect(_DB_URI, uri=True)
        self._keep_alive.execute("PRAGMA journal_mode=WAL")

        self._create_schema()
        logger.info("Repository initialised (in-memory SQLite, data_root=%s)", data_root)

    def set_emit(self, emit_fn: EmitFn) -> None:
        """Set the Tauri emit function (available after app handle is created)."""
        self._emit_fn = emit_fn

    def _emit_data_changed(self, changes: list[dict]) -> None:
        """Emit ``gera://data-changed`` if an emit function has been set.

        Args:
            changes: List of dicts like ``{"entity": "events", "ids": ["e1", "e2"]}``.
                     Use ``ids: None`` when specific IDs are unknown.
        """
        if self._emit_fn is None:
            return
        payload = json.dumps({"changes": changes})
        try:
            self._emit_fn(DATA_CHANGED_EVENT, payload)
            logger.debug("Emitted %s: %s", DATA_CHANGED_EVENT, payload)
        except Exception:
            logger.exception("Failed to emit %s", DATA_CHANGED_EVENT)

    def emit_data_changed(self, changes: list[dict]) -> None:
        """Public wrapper for emitting ``gera://data-changed``.

        Args:
            changes: List of dicts like ``{"entity": "events", "ids": ["e1"]}``.
        """
        self._emit_data_changed(changes)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_schema(self) -> None:
        """Create tables if they don't exist yet."""
        with self._conn() as db:
            db.executescript(
                """\
                CREATE TABLE IF NOT EXISTS events (
                    id          TEXT PRIMARY KEY,
                    source      TEXT NOT NULL DEFAULT 'local',
                    from_       TEXT NOT NULL,
                    to_         TEXT NOT NULL,
                    name        TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    participants TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    location    TEXT NOT NULL DEFAULT '',
                    metadata    TEXT NOT NULL DEFAULT '{}'   -- JSON-encoded EventMetadata
                );

                CREATE TABLE IF NOT EXISTS notes (
                    filename     TEXT PRIMARY KEY,
                    title        TEXT NOT NULL,
                    body_preview TEXT NOT NULL DEFAULT '',
                    event_ids    TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    project_ids  TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    raw_content  TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id           TEXT PRIMARY KEY,
                    filename     TEXT NOT NULL,
                    title        TEXT NOT NULL,
                    body_preview TEXT NOT NULL DEFAULT '',
                    event_ids    TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    raw_content  TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    rowid                INTEGER PRIMARY KEY AUTOINCREMENT,
                    text                 TEXT NOT NULL,
                    completed            INTEGER NOT NULL DEFAULT 0,
                    raw_line             TEXT NOT NULL,
                    source_file          TEXT NOT NULL,
                    line_number          INTEGER NOT NULL,
                    deadline             TEXT,            -- ISO datetime or NULL
                    event_ids            TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    project_ids          TEXT NOT NULL DEFAULT '[]',  -- JSON array
                    time_references      TEXT NOT NULL DEFAULT '[]',  -- JSON array of {modifier,amount,unit,target_id}
                    resolved_event_names TEXT NOT NULL DEFAULT '{}',  -- JSON object {event_id: name}
                    resolved_project_names TEXT NOT NULL DEFAULT '{}'  -- JSON object {project_id: title}
                );

                -- FTS5 virtual tables for full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                    id, name, description, location, participants,
                    content='events', content_rowid='rowid'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    filename, title, raw_content,
                    content='notes', content_rowid='rowid'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS projects_fts USING fts5(
                    id, title, raw_content,
                    content='projects', content_rowid='rowid'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                    text,
                    content='tasks', content_rowid='rowid'
                );
                """
            )
            # Migrations: add metadata column if it doesn't exist (for existing databases)
            try:
                db.execute("ALTER TABLE events ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'")
                db.commit()
            except db.OperationalError:
                # Column already exists, continue
                pass

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Open a new shared connection to the in-memory database."""
        conn = sqlite3.connect(_DB_URI, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # File-system readers (private — parse files → entity lists)
    # ------------------------------------------------------------------

    def _read_events_from_disk(self) -> list[EventEntity]:
        """Parse ``events.yaml`` and return a list of event entities."""
        path = events_file(self._data_root)
        if not path.exists():
            logger.debug("Events file not found: %s", path)
            return []

        logger.debug("Reading events from disk: %s", path)
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
        except Exception:
            logger.exception("Failed to parse %s", path)
            return []

        if not isinstance(data, dict) or "events" not in data:
            logger.warning("Events file is malformed or missing 'events' key: %s", path)
            return []

        events: list[EventEntity] = []
        skipped = 0
        for entry in data["events"]:
            if not isinstance(entry, dict):
                skipped += 1
                continue
            try:
                # Parse metadata from YAML, defaulting to empty metadata for backward compat
                metadata_dict = entry.get("metadata", {})
                if isinstance(metadata_dict, dict):
                    metadata = EventMetadata(**metadata_dict)
                else:
                    metadata = EventMetadata()

                events.append(
                    EventEntity(
                        id=str(entry.get("id", "")),
                        source=str(entry.get("source", "local")),
                        from_=_parse_datetime(entry.get("from", "")),
                        to=_parse_datetime(entry.get("to", "")),
                        name=str(entry.get("name", "Untitled")),
                        description=str(entry.get("description", "")),
                        participants=[str(p) for p in entry.get("participants", [])],
                        location=str(entry.get("location", "")),
                        metadata=metadata,
                    )
                )
            except Exception:
                logger.warning("Skipping malformed event entry: %s", entry)
                skipped += 1

        logger.debug("Loaded %d events from disk (%d skipped)", len(events), skipped)
        return events

    def _read_note_file(self, md_file: Path) -> tuple[NoteEntity, list[TaskEntity]]:
        """Read a single note markdown file and return (note, tasks)."""
        note_rel = md_file.relative_to(notes_dir(self._data_root)).as_posix()
        logger.debug("Reading note file: %s", note_rel)
        raw = md_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        title = extract_title(body)
        inherited_events = fm.get("event_ids", []) or []
        inherited_projects = fm.get("project_ids", []) or []
        note_tasks = self._parse_tasks_from_markdown(raw, source_file=f"notes/{note_rel}")
        for t in note_tasks:
            t.event_ids = list(set(t.event_ids) | set(inherited_events))
            t.project_ids = list(set(t.project_ids) | set(inherited_projects))
        note = NoteEntity(
            filename=note_rel,
            title=title,
            body_preview=body_preview(body),
            event_ids=inherited_events,
            project_ids=inherited_projects,
            raw_content=raw,
        )
        logger.debug("Note file loaded: %s (title: %s, %d tasks)", note_rel, title, len(note_tasks))
        return note, note_tasks

    def _read_notes_from_disk(self) -> tuple[list[NoteEntity], list[TaskEntity]]:
        """Read all ``.md`` files from ``notes/`` and return note entities."""
        ndir = notes_dir(self._data_root)
        if not ndir.is_dir():
            logger.debug("Notes directory not found: %s", ndir)
            return [], []

        logger.debug("Reading notes from directory: %s", ndir)
        notes: list[NoteEntity] = []
        all_tasks: list[TaskEntity] = []
        failed = 0
        for md_file in sorted(ndir.glob("**/*.md")):
            try:
                note, tasks = self._read_note_file(md_file)
                notes.append(note)
                all_tasks.extend(tasks)
            except Exception:
                logger.warning("Failed to read note %s", md_file, exc_info=True)
                failed += 1

        logger.info("Loaded %d notes (%d tasks, %d failed)", len(notes), len(all_tasks), failed)
        return notes, all_tasks

    def _read_project_file(self, md_file: Path) -> tuple[ProjectEntity, list[TaskEntity]]:
        """Read a single project markdown file and return (project, tasks)."""
        project_rel = md_file.relative_to(projects_dir(self._data_root)).as_posix()
        logger.debug("Reading project file: %s", project_rel)
        raw = md_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        title = extract_title(body)
        inherited_events = fm.get("event_ids", []) or []
        project_tasks = self._parse_tasks_from_markdown(
            raw, source_file=f"projects/{project_rel}"
        )
        for t in project_tasks:
            t.event_ids = list(set(t.event_ids) | set(inherited_events))
            t.project_ids = list(set(t.project_ids) | {md_file.stem})
        project = ProjectEntity(
            id=md_file.stem,
            filename=project_rel,
            title=title,
            body_preview=body_preview(body),
            event_ids=inherited_events,
            raw_content=raw,
        )
        logger.debug("Project file loaded: %s (id: %s, %d tasks)", project_rel, md_file.stem, len(project_tasks))
        return project, project_tasks

    def _read_projects_from_disk(self) -> tuple[list[ProjectEntity], list[TaskEntity]]:
        """Read all ``.md`` files from ``projects/`` and return project entities + tasks."""
        pdir = projects_dir(self._data_root)
        if not pdir.is_dir():
            logger.debug("Projects directory not found: %s", pdir)
            return [], []

        logger.debug("Reading projects from directory: %s", pdir)
        projects: list[ProjectEntity] = []
        all_tasks: list[TaskEntity] = []
        failed = 0
        for md_file in sorted(pdir.glob("**/*.md")):
            try:
                project, tasks = self._read_project_file(md_file)
                projects.append(project)
                all_tasks.extend(tasks)
            except Exception:
                logger.warning("Failed to read project %s", md_file, exc_info=True)
                failed += 1

        logger.info("Loaded %d projects (%d tasks, %d failed)", len(projects), len(all_tasks), failed)
        return projects, all_tasks

    def _read_tasks_from_disk(self) -> list[TaskEntity]:
        """Parse ``tasks.md`` for standalone floating tasks."""
        path = tasks_file(self._data_root)
        if not path.exists():
            logger.debug("Tasks file not found: %s", path)
            return []

        logger.debug("Reading tasks from disk: %s", path)
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed to read %s", path)
            return []

        tasks = self._parse_tasks_from_markdown(raw, source_file="tasks.md")
        logger.debug("Loaded %d floating tasks", len(tasks))
        return tasks

    def _parse_tasks_from_markdown(
        self, text: str, source_file: str = "tasks.md"
    ) -> list[TaskEntity]:
        """Parse markdown content for task entities."""
        tasks: list[TaskEntity] = []
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            match = _TASK_PAT.match(stripped)
            if not match:
                continue

            task_text = match.group(2)
            completed = match.group(1) in "xX"

            # Extract references from the task text
            deadline: datetime | None = None
            event_ids: list[str] = []
            project_ids: list[str] = []

            time_references: list[TimeReference] = []

            for m in _TIME_PAT.finditer(task_text):
                if m.group(1):
                    # Absolute datetime: @2026-02-20T09:00
                    try:
                        deadline = datetime.fromisoformat(m.group(1))
                    except ValueError:
                        pass
                elif m.group(2):
                    # Modifier reference: @before[30m]:standup-feb-20
                    event_ids.append(m.group(5))
                    time_references.append(
                        TimeReference(
                            modifier=m.group(2),
                            amount=int(m.group(3)),
                            unit=m.group(4),
                            target_id=m.group(5),
                        )
                    )
                elif m.group(6):
                    # Plain event reference: @event-id
                    event_ids.append(m.group(6))

            for m in _PROJECT_PAT.finditer(task_text):
                project_ids.append(m.group(1))

            tasks.append(
                TaskEntity(
                    text=task_text,
                    completed=completed,
                    raw_line=line,
                    source_file=source_file,
                    line_number=i,
                    deadline=deadline,
                    event_ids=event_ids,
                    project_ids=project_ids,
                    time_references=time_references,
                )
            )
        return tasks

    # ------------------------------------------------------------------
    # Task resolution
    # ------------------------------------------------------------------

    # Offset units → timedelta kwargs (approximate for months/years)
    _OFFSET_MAP: dict[str, str] = {
        "m": "minutes",
        "h": "hours",
        "d": "days",
        "W": "weeks",
        "M": "days",
        "Y": "days",
    }
    _OFFSET_MULTIPLIER: dict[str, int] = {
        "m": 1,
        "h": 1,
        "d": 1,
        "W": 1,
        "M": 30,
        "Y": 365,
    }

    @staticmethod
    def _compute_offset(amount: int, unit: str) -> timedelta:
        kwarg = Repository._OFFSET_MAP.get(unit, "days")
        multiplier = Repository._OFFSET_MULTIPLIER.get(unit, 1)
        return timedelta(**{kwarg: amount * multiplier})

    def _resolve_tasks(self, tasks: list[TaskEntity]) -> list[TaskEntity]:
        """Resolve event/project references against the DB.

        Populates ``resolved_event_names``, ``resolved_project_names``,
        and computes ``deadline`` from ``@before``/``@after`` time references.
        Called during ``reload_tasks()`` before insertion.
        """
        if not tasks:
            return []

        logger.debug("Resolving %d tasks...", len(tasks))
        # Collect all referenced IDs for batch lookup
        all_event_ids: set[str] = set()
        all_project_ids: set[str] = set()
        for t in tasks:
            all_event_ids.update(t.event_ids)
            all_project_ids.update(t.project_ids)

        logger.debug("Task references: %d unique events, %d unique projects", len(all_event_ids), len(all_project_ids))

        # Batch-resolve from DB
        event_map: dict[str, tuple[str, datetime, datetime]] = {}
        project_map: dict[str, str] = {}
        with self._conn() as db:
            if all_event_ids:
                event_placeholders = ",".join("?" * len(all_event_ids))
                event_rows = db.execute(
                    f"SELECT id, name, from_, to_ FROM events WHERE id IN ({event_placeholders})",
                    tuple(all_event_ids),
                ).fetchall()
                event_map = {
                    r["id"]: (
                        r["name"],
                        datetime.fromisoformat(r["from_"]),
                        datetime.fromisoformat(r["to_"]),
                    )
                    for r in event_rows
                }
                logger.debug("Resolved %d/%d event references", len(event_map), len(all_event_ids))

            if all_project_ids:
                project_placeholders = ",".join("?" * len(all_project_ids))
                project_rows = db.execute(
                    f"SELECT id, title FROM projects WHERE id IN ({project_placeholders})",
                    tuple(all_project_ids),
                ).fetchall()
                project_map = {r["id"]: r["title"] for r in project_rows}
                logger.debug("Resolved %d/%d project references", len(project_map), len(all_project_ids))

        # Enrich each task
        resolved: list[TaskEntity] = []
        unresolved_time_refs = 0
        for task in tasks:
            event_names = {
                eid: event_map[eid][0]
                for eid in task.event_ids
                if eid in event_map
            }
            project_names = {
                pid: project_map[pid]
                for pid in task.project_ids
                if pid in project_map
            }

            computed_deadline = task.deadline
            if computed_deadline is None:
                for ref in task.time_references:
                    target = event_map.get(ref.target_id)
                    if target is None:
                        logger.debug("Unresolved time ref target: %s", ref.target_id)
                        unresolved_time_refs += 1
                        continue
                    _name, from_dt, to_dt = target
                    offset = self._compute_offset(ref.amount, ref.unit)
                    if ref.modifier == "before":
                        computed_deadline = from_dt - offset
                    elif ref.modifier == "after":
                        computed_deadline = to_dt + offset
                    break  # first resolvable reference wins

            resolved.append(
                task.model_copy(
                    update={
                        "resolved_event_names": event_names,
                        "resolved_project_names": project_names,
                        "deadline": computed_deadline,
                    }
                )
            )
        
        if unresolved_time_refs > 0:
            logger.debug("Tasks with unresolved time references: %d", unresolved_time_refs)
        logger.debug("Task resolution complete: %d tasks resolved", len(resolved))
        return resolved

    @staticmethod
    def _row_to_task(r: sqlite3.Row) -> TaskEntity:
        """Convert a SQLite Row to a TaskEntity."""
        return TaskEntity(
            text=r["text"],
            completed=bool(r["completed"]),
            raw_line=r["raw_line"],
            source_file=r["source_file"],
            line_number=r["line_number"],
            deadline=datetime.fromisoformat(r["deadline"]) if r["deadline"] else None,
            event_ids=json.loads(r["event_ids"]),
            project_ids=json.loads(r["project_ids"]),
            time_references=[
                TimeReference(**tr) for tr in json.loads(r["time_references"])
            ],
            resolved_event_names=json.loads(r["resolved_event_names"]),
            resolved_project_names=json.loads(r["resolved_project_names"]),
        )

    @staticmethod
    def _task_to_row(t: TaskEntity) -> tuple:
        """Convert a TaskEntity to a row tuple for INSERT."""
        return (
            t.text,
            int(t.completed),
            t.raw_line,
            t.source_file,
            t.line_number,
            t.deadline.isoformat() if t.deadline else None,
            json.dumps(t.event_ids),
            json.dumps(t.project_ids),
            json.dumps([tr.model_dump() for tr in t.time_references]),
            json.dumps(t.resolved_event_names),
            json.dumps(t.resolved_project_names),
        )

    # ------------------------------------------------------------------
    # Reload from disk
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Re-read all entities from disk and replace database contents.

        Used at startup before emit is available — does NOT emit data-changed.
        """
        logger.debug("Repository full reload triggered")
        self.reload_events()
        self.reload_notes(resolve=False)
        self.reload_projects(resolve=False)
        self.reload_tasks(resolve=False)
        self._resolve_all_tasks()

    def reload_for_changes(self, changed_paths: list[str]) -> None:
        """Reload only the entity tables affected by the given relative paths.

        After reloading, emits ``gera://data-changed`` with the affected types.

        Args:
            changed_paths: List of paths relative to data_root,
                           e.g. ``["events.yaml", "notes/standup.md"]``.
        """
        targets: set[str] = set()
        note_files: list[str] = []
        project_files: list[str] = []

        for p in changed_paths:
            rel_parts = Path(p).parts
            if not rel_parts:
                continue
            first = rel_parts[0]
            if first in ("events.yaml", "events.yml"):
                targets.add("events")
            elif first == "tasks.md":
                targets.add("tasks")
            elif first == "notes" and len(rel_parts) > 1:
                targets.add("notes")
                note_files.append(Path(*rel_parts[1:]).as_posix())
            elif first == "projects" and len(rel_parts) > 1:
                targets.add("projects")
                project_files.append(Path(*rel_parts[1:]).as_posix())

        if not targets:
            logger.debug("No recognised entity paths in changes, skipping reload")
            return

        logger.debug("Granular reload for: %s", targets)
        if "events" in targets:
            self.reload_events()
        if "notes" in targets:
            self.reload_notes(files=note_files, resolve=False)
        if "projects" in targets:
            self.reload_projects(files=project_files, resolve=False)
        if "tasks" in targets:
            self.reload_tasks(resolve=False)

        # Any change can affect task resolution (event names, deadlines, etc.)
        self._resolve_all_tasks()
        targets.add("tasks")

        # Emit data-changed with affected entity types (ids unknown for fs changes)
        self._emit_data_changed(
            [{"entity": t, "ids": None} for t in sorted(targets)]
        )

    def reload_events(self) -> None:
        """Reload only the events table from disk."""
        logger.debug("Reloading events table from disk")
        events = self._read_events_from_disk()
        with self._conn() as db:
            db.execute("DELETE FROM events")
            db.executemany(
                "INSERT INTO events (id, source, from_, to_, name, description, participants, location, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        e.id,
                        e.source,
                        e.from_.isoformat(),
                        e.to.isoformat(),
                        e.name,
                        e.description,
                        json.dumps(e.participants),
                        e.location,
                        json.dumps(e.metadata.model_dump(mode="json")),
                    )
                    for e in events
                ],
            )
            db.execute("INSERT INTO events_fts(events_fts) VALUES('rebuild')")
            db.commit()
        logger.info("Events table reloaded: %d events", len(events))

    def _note_to_row(self, n: NoteEntity) -> tuple:
        return (
            n.filename,
            n.title,
            n.body_preview,
            json.dumps(n.event_ids),
            json.dumps(n.project_ids),
            n.raw_content,
        )

    _NOTE_INSERT_SQL = (
        "INSERT INTO notes (filename, title, body_preview, event_ids, project_ids, raw_content) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )

    def reload_notes(
        self, *, files: list[str] | None = None, resolve: bool = True
    ) -> None:
        """Reload notes and their embedded tasks from disk.

        Args:
            files: Optional list of note filenames (e.g. ``["meeting.md"]``).
                   When provided, only those notes are re-read (or removed if
                   the file no longer exists on disk).  ``None`` means full reload.
            resolve: Whether to resolve all task references afterwards.
        """
        if files is None:
            # Full reload
            logger.debug("Full reload of notes table")
            notes, note_tasks = self._read_notes_from_disk()
            with self._conn() as db:
                db.execute("DELETE FROM notes")
                db.executemany(self._NOTE_INSERT_SQL, [self._note_to_row(n) for n in notes])
                self._rebuild_notes_fts(db)
                db.commit()
            note_sources = {f"notes/{n.filename}" for n in notes}
            self._replace_tasks(note_sources, note_tasks)
            logger.info("Notes table reloaded (full): %d notes, %d tasks", len(notes), len(note_tasks))
        else:
            # Partial reload — only the specified files
            logger.debug("Partial reload of notes: %s", files)
            ndir = notes_dir(self._data_root)
            all_note_tasks: list[TaskEntity] = []
            source_files: set[str] = set()
            with self._conn() as db:
                for filename in files:
                    source_files.add(f"notes/{filename}")
                    db.execute("DELETE FROM notes WHERE filename = ?", (filename,))
                    md_path = ndir / filename
                    if md_path.exists():
                        try:
                            note, tasks = self._read_note_file(md_path)
                            db.execute(self._NOTE_INSERT_SQL, self._note_to_row(note))
                            all_note_tasks.extend(tasks)
                            logger.debug("Reloaded note: %s", filename)
                        except Exception:
                            logger.warning("Failed to read note %s", md_path, exc_info=True)
                    else:
                        logger.debug("Note file deleted: %s", filename)
                self._rebuild_notes_fts(db)
                db.commit()
            self._replace_tasks(source_files, all_note_tasks)
            logger.info("Notes table reloaded (partial): %d files, %d tasks", len(files), len(all_note_tasks))

        if resolve:
            self._resolve_all_tasks()

    def _project_to_row(self, p: ProjectEntity) -> tuple:
        return (
            p.id,
            p.filename,
            p.title,
            p.body_preview,
            json.dumps(p.event_ids),
            p.raw_content,
        )

    _PROJECT_INSERT_SQL = (
        "INSERT INTO projects (id, filename, title, body_preview, event_ids, raw_content) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )

    def reload_projects(
        self, *, files: list[str] | None = None, resolve: bool = True
    ) -> None:
        """Reload projects and their embedded tasks from disk.

        Args:
            files: Optional list of project filenames (e.g. ``["website.md"]``).
                   When provided, only those projects are re-read (or removed if
                   the file no longer exists on disk).  ``None`` means full reload.
            resolve: Whether to resolve all task references afterwards.
        """
        if files is None:
            # Full reload
            logger.debug("Full reload of projects table")
            projects, project_tasks = self._read_projects_from_disk()
            with self._conn() as db:
                db.execute("DELETE FROM projects")
                db.executemany(self._PROJECT_INSERT_SQL, [self._project_to_row(p) for p in projects])
                self._rebuild_projects_fts(db)
                db.commit()
            project_sources = {f"projects/{p.filename}" for p in projects}
            self._replace_tasks(project_sources, project_tasks)
            logger.info("Projects table reloaded (full): %d projects, %d tasks", len(projects), len(project_tasks))
        else:
            # Partial reload — only the specified files
            logger.debug("Partial reload of projects: %s", files)
            pdir = projects_dir(self._data_root)
            all_project_tasks: list[TaskEntity] = []
            source_files: set[str] = set()
            with self._conn() as db:
                for filename in files:
                    project_id = Path(filename).stem
                    source_files.add(f"projects/{filename}")
                    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                    md_path = pdir / filename
                    if md_path.exists():
                        try:
                            project, tasks = self._read_project_file(md_path)
                            db.execute(self._PROJECT_INSERT_SQL, self._project_to_row(project))
                            all_project_tasks.extend(tasks)
                            logger.debug("Reloaded project: %s (id: %s)", filename, project_id)
                        except Exception:
                            logger.warning("Failed to read project %s", md_path, exc_info=True)
                    else:
                        logger.debug("Project file deleted: %s (id: %s)", filename, project_id)
                self._rebuild_projects_fts(db)
                db.commit()
            self._replace_tasks(source_files, all_project_tasks)
            logger.info("Projects table reloaded (partial): %d files, %d tasks", len(files), len(all_project_tasks))

        if resolve:
            self._resolve_all_tasks()

    def reload_tasks(self, *, resolve: bool = True) -> None:
        """Reload floating tasks from tasks.md."""
        logger.debug("Reloading floating tasks")
        tasks = self._read_tasks_from_disk()
        self._replace_tasks({"tasks.md"}, tasks)
        if resolve:
            self._resolve_all_tasks()
        logger.info("Floating tasks table reloaded: %d tasks", len(tasks))

    # ------------------------------------------------------------------
    # FTS rebuild helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rebuild_notes_fts(db: sqlite3.Connection) -> None:
        db.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")

    @staticmethod
    def _rebuild_projects_fts(db: sqlite3.Connection) -> None:
        db.execute("INSERT INTO projects_fts(projects_fts) VALUES('rebuild')")

    @staticmethod
    def _rebuild_tasks_fts(db: sqlite3.Connection) -> None:
        db.execute("INSERT INTO tasks_fts(tasks_fts) VALUES('rebuild')")

    def _replace_tasks(self, source_files: set[str], tasks: list[TaskEntity]) -> None:
        """Delete tasks for *source_files* and insert *tasks* as replacements."""
        logger.debug("Replacing tasks for sources: %s (%d new tasks)", source_files, len(tasks))
        with self._conn() as db:
            if source_files:
                placeholders = ",".join("?" * len(source_files))
                db.execute(
                    f"DELETE FROM tasks WHERE source_file IN ({placeholders})",
                    tuple(source_files),
                )
                logger.debug("Deleted old tasks from sources: %s", source_files)
            if tasks:
                db.executemany(
                    _TASKS_INSERT_SQL,
                    [self._task_to_row(t) for t in tasks],
                )
                logger.debug("Inserted %d new tasks", len(tasks))
            self._rebuild_tasks_fts(db)
            db.commit()

    def _resolve_all_tasks(self) -> None:
        """Read all tasks from DB, resolve references, and write back."""
        logger.debug("Starting full task resolution pass")
        with self._conn() as db:
            rows = db.execute("SELECT * FROM tasks").fetchall()
        tasks = [self._row_to_task(r) for r in rows]
        if not tasks:
            logger.debug("No tasks to resolve")
            return
        logger.debug("Tasks before resolution: %d", len(tasks))
        resolved = self._resolve_tasks(tasks)
        with self._conn() as db:
            db.execute("DELETE FROM tasks")
            db.executemany(
                _TASKS_INSERT_SQL,
                [self._task_to_row(t) for t in resolved],
            )
            self._rebuild_tasks_fts(db)
            db.commit()
        logger.info("Full task resolution complete: %d tasks resolved", len(resolved))

    @staticmethod
    def _normalize_page_size(limit: int | None) -> int:
        """Validate and clamp page size."""
        page_size = 100 if limit is None else limit
        if page_size < 1:
            raise ValueError("limit must be >= 1")
        return min(page_size, 500)

    @staticmethod
    def _parse_cursor(cursor: str | None) -> int:
        """Parse cursor as a numeric offset."""
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ValueError("cursor must be a non-negative integer string") from exc
        if offset < 0:
            raise ValueError("cursor must be non-negative")
        return offset

    def _run_paginated_query(
        self,
        *,
        select_sql: str,
        where_clauses: list[str],
        where_params: list[object],
        order_by_sql: str,
        limit: int | None,
        cursor: str | None,
    ) -> tuple[list[sqlite3.Row], str | None]:
        """Execute a paginated query with LIMIT/OFFSET cursor semantics."""
        page_size = self._normalize_page_size(limit)
        offset = self._parse_cursor(cursor)

        sql_parts = [select_sql]
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))
        sql_parts.append(order_by_sql)
        sql_parts.append("LIMIT ? OFFSET ?")
        sql = " ".join(sql_parts)

        params = [*where_params, page_size + 1, offset]
        with self._conn() as db:
            rows = db.execute(sql, tuple(params)).fetchall()

        has_more = len(rows) > page_size
        page_rows = rows[:page_size]
        next_cursor = str(offset + page_size) if has_more else None
        return page_rows, next_cursor

    def list_events_page(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> tuple[list[EventEntity], str | None]:
        """List events with cursor pagination and optional time-range filtering."""
        where_clauses: list[str] = []
        where_params: list[object] = []

        if from_ is not None:
            where_clauses.append("to_ >= ?")
            where_params.append(from_.isoformat())
        if to is not None:
            where_clauses.append("from_ <= ?")
            where_params.append(to.isoformat())

        rows, next_cursor = self._run_paginated_query(
            select_sql="SELECT * FROM events",
            where_clauses=where_clauses,
            where_params=where_params,
            order_by_sql="ORDER BY from_ ASC, to_ ASC, id ASC",
            limit=limit,
            cursor=cursor,
        )
        
        events = []
        for r in rows:
            # Parse metadata, handling backward compatibility
            metadata_json = r["metadata"] if r["metadata"] else "{}"
            try:
                metadata_dict = json.loads(metadata_json)
                metadata = EventMetadata(**metadata_dict)
            except Exception:
                metadata = EventMetadata()
            
            events.append(
                EventEntity(
                    id=r["id"],
                    source=r["source"],
                    from_=datetime.fromisoformat(r["from_"]),
                    to=datetime.fromisoformat(r["to_"]),
                    name=r["name"],
                    description=r["description"],
                    participants=json.loads(r["participants"]),
                    location=r["location"],
                    metadata=metadata,
                )
            )
        
        return (events, next_cursor)

    def list_notes_page(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        event_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[list[NoteEntity], str | None]:
        """List notes with cursor pagination and relationship filters."""
        where_clauses: list[str] = []
        where_params: list[object] = []

        if event_id:
            where_clauses.append("instr(event_ids, ?) > 0")
            where_params.append(f'"{event_id}"')
        if project_id:
            where_clauses.append("instr(project_ids, ?) > 0")
            where_params.append(f'"{project_id}"')

        rows, next_cursor = self._run_paginated_query(
            select_sql="SELECT * FROM notes",
            where_clauses=where_clauses,
            where_params=where_params,
            order_by_sql="ORDER BY filename ASC",
            limit=limit,
            cursor=cursor,
        )
        return (
            [
                NoteEntity(
                    filename=r["filename"],
                    title=r["title"],
                    body_preview=r["body_preview"],
                    event_ids=json.loads(r["event_ids"]),
                    project_ids=json.loads(r["project_ids"]),
                    raw_content=r["raw_content"],
                )
                for r in rows
            ],
            next_cursor,
        )

    def list_projects_page(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> tuple[list[ProjectEntity], str | None]:
        """List projects with cursor pagination."""
        rows, next_cursor = self._run_paginated_query(
            select_sql="SELECT * FROM projects",
            where_clauses=[],
            where_params=[],
            order_by_sql="ORDER BY id ASC",
            limit=limit,
            cursor=cursor,
        )
        return (
            [
                ProjectEntity(
                    id=r["id"],
                    filename=r["filename"],
                    title=r["title"],
                    body_preview=r["body_preview"],
                    event_ids=json.loads(r["event_ids"]),
                    raw_content=r["raw_content"],
                )
                for r in rows
            ],
            next_cursor,
        )

    def list_tasks_page(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        deadline_from: datetime | None = None,
        deadline_to: datetime | None = None,
        event_id: str | None = None,
        project_id: str | None = None,
    ) -> tuple[list[TaskEntity], str | None]:
        """List tasks with cursor pagination and optional time/relationship filters."""
        where_clauses: list[str] = []
        where_params: list[object] = []

        if deadline_from is not None:
            where_clauses.append("deadline IS NOT NULL")
            where_clauses.append("deadline >= ?")
            where_params.append(deadline_from.isoformat())
        if deadline_to is not None:
            where_clauses.append("deadline IS NOT NULL")
            where_clauses.append("deadline <= ?")
            where_params.append(deadline_to.isoformat())
        if event_id:
            where_clauses.append("instr(event_ids, ?) > 0")
            where_params.append(f'"{event_id}"')
        if project_id:
            where_clauses.append("instr(project_ids, ?) > 0")
            where_params.append(f'"{project_id}"')

        rows, next_cursor = self._run_paginated_query(
            select_sql="SELECT * FROM tasks",
            where_clauses=where_clauses,
            where_params=where_params,
            order_by_sql="ORDER BY source_file ASC, line_number ASC, rowid ASC",
            limit=limit,
            cursor=cursor,
        )
        return ([self._row_to_task(r) for r in rows], next_cursor)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_events(self) -> list[EventEntity]:
        events: list[EventEntity] = []
        cursor: str | None = None
        while True:
            page, next_cursor = self.list_events_page(limit=500, cursor=cursor)
            events.extend(page)
            if next_cursor is None:
                break
            cursor = next_cursor
        return events

    def list_notes(self) -> list[NoteEntity]:
        notes: list[NoteEntity] = []
        cursor: str | None = None
        while True:
            page, next_cursor = self.list_notes_page(limit=500, cursor=cursor)
            notes.extend(page)
            if next_cursor is None:
                break
            cursor = next_cursor
        return notes

    def list_projects(self) -> list[ProjectEntity]:
        projects: list[ProjectEntity] = []
        cursor: str | None = None
        while True:
            page, next_cursor = self.list_projects_page(limit=500, cursor=cursor)
            projects.extend(page)
            if next_cursor is None:
                break
            cursor = next_cursor
        return projects

    def list_tasks(self) -> list[TaskEntity]:
        tasks: list[TaskEntity] = []
        cursor: str | None = None
        while True:
            page, next_cursor = self.list_tasks_page(limit=500, cursor=cursor)
            tasks.extend(page)
            if next_cursor is None:
                break
            cursor = next_cursor
        return tasks

    def get_note(self, filename: str) -> NoteEntity | None:
        """Return a single note by filename, or None if not found."""
        with self._conn() as db:
            row = db.execute("SELECT * FROM notes WHERE filename = ?", (filename,)).fetchone()
        if row is None:
            return None
        return NoteEntity(
            filename=row["filename"],
            title=row["title"],
            body_preview=row["body_preview"],
            event_ids=json.loads(row["event_ids"]),
            project_ids=json.loads(row["project_ids"]),
            raw_content=row["raw_content"],
        )

    def get_event(self, event_id: str) -> EventEntity | None:
        """Return a single event by ID, or None if not found."""
        with self._conn() as db:
            row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        # Parse metadata, handling backward compatibility for rows without it
        metadata_json = row["metadata"] if row["metadata"] else "{}"
        try:
            metadata_dict = json.loads(metadata_json)
            metadata = EventMetadata(**metadata_dict)
        except Exception:
            metadata = EventMetadata()
        return EventEntity(
            id=row["id"],
            source=row["source"],
            from_=datetime.fromisoformat(row["from_"]),
            to=datetime.fromisoformat(row["to_"]),
            name=row["name"],
            description=row["description"],
            participants=json.loads(row["participants"]),
            location=row["location"],
            metadata=metadata,
        )

    def get_project(self, project_id: str) -> ProjectEntity | None:
        """Return a single project by ID, or None if not found."""
        with self._conn() as db:
            row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        return ProjectEntity(
            id=row["id"],
            filename=row["filename"],
            title=row["title"],
            body_preview=row["body_preview"],
            event_ids=json.loads(row["event_ids"]),
            raw_content=row["raw_content"],
        )

    # ------------------------------------------------------------------
    # Full-text search
    # ------------------------------------------------------------------

    def search_events(self, query: str) -> list[EventEntity]:
        """Full-text search across event name, description, location, participants."""
        logger.debug("Searching events: %s", query)
        wildcard = f"%{query}%"
        with self._conn() as db:
            try:
                rows = db.execute(
                    "SELECT e.* FROM events e "
                    "JOIN events_fts f ON e.rowid = f.rowid "
                    "WHERE events_fts MATCH ?",
                    (query,),
                ).fetchall()
                logger.debug("FTS search found %d events", len(rows))
            except sqlite3.OperationalError:
                logger.debug("Invalid FTS query for events; falling back to LIKE")
                rows = db.execute(
                    "SELECT * FROM events "
                    "WHERE name LIKE ? OR description LIKE ? OR location LIKE ? OR participants LIKE ?",
                    (wildcard, wildcard, wildcard, wildcard),
                ).fetchall()
                logger.debug("LIKE search found %d events", len(rows))
        
        events = []
        for r in rows:
            # Parse metadata, handling backward compatibility
            metadata_json = r["metadata"] if r["metadata"] else "{}"
            try:
                metadata_dict = json.loads(metadata_json)
                metadata = EventMetadata(**metadata_dict)
            except Exception:
                metadata = EventMetadata()
            
            events.append(
                EventEntity(
                    id=r["id"],
                    source=r["source"],
                    from_=datetime.fromisoformat(r["from_"]),
                    to=datetime.fromisoformat(r["to_"]),
                    name=r["name"],
                    description=r["description"],
                    participants=json.loads(r["participants"]),
                    location=r["location"],
                    metadata=metadata,
                )
            )
        logger.info("Event search completed: query=%s, results=%d", query, len(events))
        return events

    def search_notes(self, query: str) -> list[NoteEntity]:
        """Full-text search across note title and raw content."""
        logger.debug("Searching notes: %s", query)
        wildcard = f"%{query}%"
        with self._conn() as db:
            try:
                rows = db.execute(
                    "SELECT n.* FROM notes n "
                    "JOIN notes_fts f ON n.rowid = f.rowid "
                    "WHERE notes_fts MATCH ?",
                    (query,),
                ).fetchall()
                logger.debug("FTS search found %d notes", len(rows))
            except sqlite3.OperationalError:
                logger.debug("Invalid FTS query for notes; falling back to LIKE")
                rows = db.execute(
                    "SELECT * FROM notes WHERE title LIKE ? OR raw_content LIKE ?",
                    (wildcard, wildcard),
                ).fetchall()
                logger.debug("LIKE search found %d notes", len(rows))
        
        results = [
            NoteEntity(
                filename=r["filename"],
                title=r["title"],
                body_preview=r["body_preview"],
                event_ids=json.loads(r["event_ids"]),
                project_ids=json.loads(r["project_ids"]),
                raw_content=r["raw_content"],
            )
            for r in rows
        ]
        logger.info("Note search completed: query=%s, results=%d", query, len(results))
        return results

    def search_projects(self, query: str) -> list[ProjectEntity]:
        """Full-text search across project title and raw content."""
        logger.debug("Searching projects: %s", query)
        wildcard = f"%{query}%"
        with self._conn() as db:
            try:
                rows = db.execute(
                    "SELECT p.* FROM projects p "
                    "JOIN projects_fts f ON p.rowid = f.rowid "
                    "WHERE projects_fts MATCH ?",
                    (query,),
                ).fetchall()
                logger.debug("FTS search found %d projects", len(rows))
            except sqlite3.OperationalError:
                logger.debug("Invalid FTS query for projects; falling back to LIKE")
                rows = db.execute(
                    "SELECT * FROM projects WHERE title LIKE ? OR raw_content LIKE ?",
                    (wildcard, wildcard),
                ).fetchall()
                logger.debug("LIKE search found %d projects", len(rows))
        
        results = [
            ProjectEntity(
                id=r["id"],
                filename=r["filename"],
                title=r["title"],
                body_preview=r["body_preview"],
                event_ids=json.loads(r["event_ids"]),
                raw_content=r["raw_content"],
            )
            for r in rows
        ]
        logger.info("Project search completed: query=%s, results=%d", query, len(results))
        return results

    def search_tasks(self, query: str) -> list[TaskEntity]:
        """Full-text search across task text."""
        logger.debug("Searching tasks: %s", query)
        wildcard = f"%{query}%"
        with self._conn() as db:
            try:
                rows = db.execute(
                    "SELECT t.* FROM tasks t "
                    "JOIN tasks_fts f ON t.rowid = f.rowid "
                    "WHERE tasks_fts MATCH ? "
                    "ORDER BY t.line_number",
                    (query,),
                ).fetchall()
                logger.debug("FTS search found %d tasks", len(rows))
            except sqlite3.OperationalError:
                logger.debug("Invalid FTS query for tasks; falling back to LIKE")
                rows = db.execute(
                    "SELECT * FROM tasks WHERE text LIKE ? ORDER BY line_number",
                    (wildcard,),
                ).fetchall()
                logger.debug("LIKE search found %d tasks", len(rows))
        
        results = [self._row_to_task(r) for r in rows]
        logger.info("Task search completed: query=%s, results=%d", query, len(results))
        return results

    # ------------------------------------------------------------------
    # Write methods (file → reload → emit)
    # ------------------------------------------------------------------

    def create_note(
        self,
        filename: str,
        content: str,
        event_ids: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> NoteEntity:
        """Create a new note file on disk, reload notes, and emit.

        Args:
            filename: Note filename (with or without ``.md`` extension).
            content: Markdown body content (without frontmatter).
            event_ids: Optional list of associated event IDs.
            project_ids: Optional list of associated project IDs.

        Returns:
            The newly created NoteEntity from the repository.
        """
        logger.debug("Creating note: filename=%s, event_ids=%s, project_ids=%s", filename, event_ids, project_ids)
        frontmatter: dict = {}
        if event_ids:
            frontmatter["event_ids"] = event_ids
        if project_ids:
            frontmatter["project_ids"] = project_ids

        note_filename = Path(filename).as_posix()
        if not note_filename.endswith(".md"):
            note_filename = f"{note_filename}.md"

        full_content = serialize_frontmatter(
            frontmatter,
            content,
        )

        path = note_file(self._data_root, note_filename)
        if path.exists():
            logger.error("Note already exists: %s", path)
            raise FileExistsError(f"Note already exists: {path}")
        path.write_text(_sanitize_content(full_content), encoding="utf-8")
        logger.info("Created note file: %s", path)

        self.reload_notes(files=[note_filename])
        self._emit_data_changed([{"entity": "notes", "ids": [note_filename]}])

        note = self.get_note(note_filename)
        if note is None:
            raise RuntimeError(f"Note not found after creation: {note_filename}")
        return note

    def update_note(self, filename: str, content: str) -> NoteEntity:
        """Overwrite a note file with new content, reload, and emit.

        Args:
            filename: Note filename.
            content: Full raw file content (frontmatter + body).

        Returns:
            The updated NoteEntity.
        """
        logger.debug("Updating note: filename=%s", filename)
        note_filename = Path(filename).as_posix()
        if not note_filename.endswith(".md"):
            note_filename = f"{note_filename}.md"

        path = note_file(self._data_root, note_filename)
        if not path.exists():
            logger.error("Note not found: %s", path)
            raise FileNotFoundError(f"Note not found: {path}")
        path.write_text(_sanitize_content(content), encoding="utf-8")
        logger.info("Updated note file: %s", path)

        self.reload_notes(files=[note_filename])
        self._emit_data_changed([{"entity": "notes", "ids": [note_filename]}])

        note = self.get_note(note_filename)
        if note is None:
            raise RuntimeError(f"Note not found after update: {note_filename}")
        return note

    def delete_note(self, filename: str) -> None:
        """Delete a note file from disk, reload, and emit.

        Args:
            filename: Note filename.
        """
        logger.debug("Deleting note: filename=%s", filename)
        note_filename = Path(filename).as_posix()
        if not note_filename.endswith(".md"):
            note_filename = f"{note_filename}.md"

        path = note_file(self._data_root, note_filename)
        if not path.exists():
            logger.error("Note not found: %s", path)
            raise FileNotFoundError(f"Note not found: {path}")
        path.unlink()
        logger.info("Deleted note file: %s", path)

        self.reload_notes(files=[note_filename])
        self._emit_data_changed([{"entity": "notes", "ids": [note_filename]}])

    def create_project(
        self,
        filename: str,
        content: str,
        event_ids: list[str] | None = None,
    ) -> ProjectEntity:
        """Create a new project file on disk, reload projects, and emit.

        Args:
            filename: Project filename (with or without ``.md`` extension).
            content: Markdown body content (without frontmatter).
            event_ids: Optional list of associated event IDs.

        Returns:
            The newly created ProjectEntity.
        """
        logger.debug("Creating project: filename=%s, event_ids=%s", filename, event_ids)
        frontmatter: dict = {}
        if event_ids:
            frontmatter["event_ids"] = event_ids

        project_filename = Path(filename).as_posix()
        if not project_filename.endswith(".md"):
            project_filename = f"{project_filename}.md"

        title = Path(project_filename).stem
        full_content = serialize_frontmatter(frontmatter, f"# {title}\n\n{content}")

        path = project_file(self._data_root, project_filename)
        if path.exists():
            logger.error("Project already exists: %s", path)
            raise FileExistsError(f"Project already exists: {path}")
        path.write_text(_sanitize_content(full_content), encoding="utf-8")
        logger.info("Created project file: %s (id: %s)", path, Path(project_filename).stem)

        self.reload_projects(files=[project_filename])
        project_id = Path(project_filename).stem
        self._emit_data_changed([{"entity": "projects", "ids": [project_id]}])

        project = self.get_project(project_id)
        if project is None:
            raise RuntimeError(f"Project not found after creation: {project_id}")
        return project

    def update_project(self, filename: str, content: str) -> ProjectEntity:
        """Overwrite a project file with new content, reload, and emit.

        Args:
            filename: Project filename.
            content: Full raw file content (frontmatter + body).

        Returns:
            The updated ProjectEntity.
        """
        logger.debug("Updating project: filename=%s", filename)
        project_filename = Path(filename).as_posix()
        if not project_filename.endswith(".md"):
            project_filename = f"{project_filename}.md"

        path = project_file(self._data_root, project_filename)
        if not path.exists():
            logger.error("Project not found: %s", path)
            raise FileNotFoundError(f"Project not found: {path}")
        path.write_text(_sanitize_content(content), encoding="utf-8")
        logger.info("Updated project file: %s", path)

        self.reload_projects(files=[project_filename])
        project_id = Path(project_filename).stem
        self._emit_data_changed([{"entity": "projects", "ids": [project_id]}])

        project = self.get_project(project_id)
        if project is None:
            raise RuntimeError(f"Project not found after update: {project_id}")
        return project

    def delete_project(self, filename: str) -> None:
        """Delete a project file from disk, reload, and emit.

        Args:
            filename: Project filename.
        """
        logger.debug("Deleting project: filename=%s", filename)
        project_filename = Path(filename).as_posix()
        if not project_filename.endswith(".md"):
            project_filename = f"{project_filename}.md"

        path = project_file(self._data_root, project_filename)
        if not path.exists():
            logger.error("Project not found: %s", path)
            raise FileNotFoundError(f"Project not found: {path}")
        path.unlink()
        logger.info("Deleted project file: %s", path)

        self.reload_projects(files=[project_filename])
        project_id = Path(project_filename).stem
        self._emit_data_changed([{"entity": "projects", "ids": [project_id]}])

    def create_event(self, event: EventEntity) -> EventEntity:
        """Append a new event to events.yaml, reload, and emit.

        Args:
            event: The event entity to create.

        Returns:
            The created EventEntity as read back from the repository.
        """
        logger.debug("Creating event: id=%s, name=%s, from=%s, to=%s", event.id, event.name, event.from_.isoformat(), event.to.isoformat())
        path = events_file(self._data_root)
        raw = path.read_text(encoding="utf-8") if path.exists() else "events: []\n"
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or "events" not in data:
            data = {"events": []}
        if not isinstance(data["events"], list):
            raise ValueError("events.yaml is malformed")

        if any(isinstance(existing, dict) and existing.get("id") == event.id for existing in data["events"]):
            logger.error("Event already exists: %s", event.id)
            raise FileExistsError(f"Event already exists: {event.id}")

        entry = {
            "id": event.id,
            "source": event.source,
            "from": event.from_.isoformat(),
            "to": event.to.isoformat(),
            "name": event.name,
            "description": event.description,
            "participants": event.participants,
            "location": event.location,
            "metadata": json.loads(event.metadata.model_dump_json()),
        }
        data["events"].append(entry)
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
        logger.info("Created event: %s", event.id)

        self.reload_events()
        self._emit_data_changed([{"entity": "events", "ids": [event.id]}])

        created = self.get_event(event.id)
        if created is None:
            raise RuntimeError(f"Event not found after creation: {event.id}")
        return created

    def update_event(self, event: EventEntity) -> EventEntity:
        """Update an existing event in events.yaml, reload, and emit.

        Finds the event by ID and replaces it.

        Args:
            event: The event entity with updated fields.

        Returns:
            The updated EventEntity.
        """
        logger.debug("Updating event: id=%s, name=%s", event.id, event.name)
        path = events_file(self._data_root)
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or "events" not in data:
            raise ValueError("events.yaml is malformed")

        found = False
        for i, entry in enumerate(data["events"]):
            if isinstance(entry, dict) and entry.get("id") == event.id:
                data["events"][i] = {
                    "id": event.id,
                    "source": event.source,
                    "from": event.from_.isoformat(),
                    "to": event.to.isoformat(),
                    "name": event.name,
                    "description": event.description,
                    "participants": event.participants,
                    "location": event.location,
                    "metadata": json.loads(event.metadata.model_dump_json()),
                }
                found = True
                break

        if not found:
            logger.error("Event not found for update: %s", event.id)
            raise KeyError(f"Event not found: {event.id}")

        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
        logger.info("Updated event: %s", event.id)

        self.reload_events()
        self._emit_data_changed([{"entity": "events", "ids": [event.id]}])

        updated = self.get_event(event.id)
        if updated is None:
            raise RuntimeError(f"Event not found after update: {event.id}")
        return updated

    def delete_event(self, event_id: str) -> None:
        """Remove an event from events.yaml, reload, and emit.

        Args:
            event_id: The ID of the event to delete.
        """
        logger.debug("Deleting event: %s", event_id)
        path = events_file(self._data_root)
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or "events" not in data:
            raise ValueError("events.yaml is malformed")

        original_len = len(data["events"])
        data["events"] = [
            e for e in data["events"]
            if not (isinstance(e, dict) and e.get("id") == event_id)
        ]
        if len(data["events"]) == original_len:
            logger.error("Event not found for deletion: %s", event_id)
            raise KeyError(f"Event not found: {event_id}")

        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
        logger.info("Deleted event: %s", event_id)

        self.reload_events()
        self._emit_data_changed([{"entity": "events", "ids": [event_id]}])

    def toggle_task(self, source_file: str, line_number: int) -> None:
        """Toggle a task's completion status in its source markdown file.

        Finds the line at ``line_number`` in ``source_file``, toggles
        ``- [ ]`` ↔ ``- [x]``, writes back, reloads tasks, and emits.

        Args:
            source_file: Relative path to the source file (e.g. ``tasks.md``).
            line_number: 1-based line number of the task in the file.
        """
        logger.debug("Toggling task: source_file=%s, line_number=%d", source_file, line_number)
        path = self._data_root / source_file
        if not path.exists():
            logger.error("Source file not found: %s", path)
            raise FileNotFoundError(f"Source file not found: {path}")

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        idx = line_number - 1  # 0-based
        if idx < 0 or idx >= len(lines):
            logger.error("Line %d out of range in %s", line_number, source_file)
            raise IndexError(f"Line {line_number} out of range in {source_file}")

        line = lines[idx]
        line_no_newline = line.rstrip("\n")
        newline = line[len(line_no_newline):]
        match = re.match(r"^(\s*)([-*+]) \[([ xX])\] (.+)$", line_no_newline)
        if match is None:
            logger.error("Line %d is not a task: %s", line_number, line)
            raise ValueError(f"Line {line_number} is not a task: {line!r}")

        indent, bullet, marker, task_text = match.groups()
        toggled_marker = " " if marker in "xX" else "x"
        old_status = "completed" if marker in "xX" else "incomplete"
        new_status = "incomplete" if marker in "xX" else "completed"
        lines[idx] = f"{indent}{bullet} [{toggled_marker}] {task_text}{newline}"

        path.write_text(_sanitize_content("".join(lines)), encoding="utf-8")
        logger.info("Toggled task at %s:%d (%s → %s)", source_file, line_number, old_status, new_status)

        # Reload the entity that owns this task
        if source_file.startswith("notes/"):
            self.reload_notes()
        elif source_file.startswith("projects/"):
            self.reload_projects()
        else:
            self.reload_tasks()
        self._emit_data_changed([{"entity": "tasks", "ids": None}])

    def delete_task(self, source_file: str, line_number: int) -> None:
        """Remove a task line from its source file, reload, and emit.

        Args:
            source_file: Relative path to the source file.
            line_number: 1-based line number of the task.
        """
        logger.debug("Deleting task: source_file=%s, line_number=%d", source_file, line_number)
        path = self._data_root / source_file
        if not path.exists():
            logger.error("Source file not found: %s", path)
            raise FileNotFoundError(f"Source file not found: {path}")

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        idx = line_number - 1
        if idx < 0 or idx >= len(lines):
            logger.error("Line %d out of range in %s", line_number, source_file)
            raise IndexError(f"Line {line_number} out of range in {source_file}")

        match = re.match(r"^\s*[-*+] \[[ xX]\] ", lines[idx])
        if match is None:
            logger.error("Line %d is not a task: %s", line_number, lines[idx])
            raise ValueError(f"Line {line_number} is not a task: {lines[idx]!r}")

        del lines[idx]
        path.write_text(_sanitize_content("".join(lines)), encoding="utf-8")
        logger.info("Deleted task at %s:%d", source_file, line_number)

        if source_file.startswith("notes/"):
            self.reload_notes()
        elif source_file.startswith("projects/"):
            self.reload_projects()
        else:
            self.reload_tasks()
        self._emit_data_changed([{"entity": "tasks", "ids": None}])

    def update_task(self, source_file: str, line_number: int, new_text: str) -> None:
        """Rewrite the text of an existing task line, preserving its completion state.

        Args:
            source_file: Relative path to the source file (e.g. ``tasks.md``).
            line_number: 1-based line number of the task in the file.
            new_text: New task description (without the ``- [ ] `` prefix).
        """
        new_text = new_text.strip()
        if not new_text:
            raise ValueError("Task text must not be empty")

        logger.debug("Updating task: source_file=%s, line_number=%d, new_text=%s", source_file, line_number, new_text[:50])
        path = self._data_root / source_file
        if not path.exists():
            logger.error("Source file not found: %s", path)
            raise FileNotFoundError(f"Source file not found: {path}")

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        idx = line_number - 1
        if idx < 0 or idx >= len(lines):
            logger.error("Line %d out of range in %s", line_number, source_file)
            raise IndexError(f"Line {line_number} out of range in {source_file}")

        line = lines[idx]
        line_no_newline = line.rstrip("\n")
        newline = line[len(line_no_newline):]
        match = re.match(r"^(\s*)([-*+]) \[([ xX])\] .+$", line_no_newline)
        if match is None:
            logger.error("Line %d is not a task: %s", line_number, line)
            raise ValueError(f"Line {line_number} is not a task: {line!r}")

        indent, bullet, marker = match.group(1), match.group(2), match.group(3)
        lines[idx] = f"{indent}{bullet} [{marker}] {new_text}{newline}"

        path.write_text(_sanitize_content("".join(lines)), encoding="utf-8")
        logger.info("Updated task at %s:%d", source_file, line_number)

        if source_file.startswith("notes/"):
            self.reload_notes()
        elif source_file.startswith("projects/"):
            self.reload_projects()
        else:
            self.reload_tasks()
        self._emit_data_changed([{"entity": "tasks", "ids": None}])

    def create_task(self, text: str) -> TaskEntity:
        """Append a new uncompleted task to ``tasks.md``, reload, and emit.

        Args:
            text: The task text (without the ``- [ ]`` prefix).

        Returns:
            The newly created TaskEntity from the repository.
        """
        text = text.strip()
        if not text:
            raise ValueError("Task text must not be empty")

        logger.debug("Creating task: text=%s", text[:60])
        path = tasks_file(self._data_root)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""

        # Ensure the new task starts on its own line
        if existing and not existing.endswith("\n"):
            existing += "\n"

        new_line = f"- [ ] {text}\n"
        path.write_text(_sanitize_content(existing + new_line), encoding="utf-8")
        logger.info("Created task: %s", text[:60])

        self.reload_tasks()
        self._emit_data_changed([{"entity": "tasks", "ids": None}])

        # Return the last task from tasks.md (the one we just appended)
        tasks = self.list_tasks()
        floating = [t for t in tasks if t.source_file == "tasks.md"]
        if not floating:
            raise RuntimeError("Task not found after creation")
        return floating[-1]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the keep-alive connection, releasing the in-memory database."""
        self._keep_alive.close()
        logger.info("Repository closed")
