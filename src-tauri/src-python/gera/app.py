import json
import logging
from datetime import datetime
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic import BaseModel
from pytauri import (
    Commands,
    builder_factory,
    context_factory,
)


from gera.entities import (
    EventEntity,
    NoteEntity,
    ProjectEntity,
    TaskEntity,
)
from gera.filesystem import init_data_directory, verify_structure
from gera.renderer import render as render_markdown
from gera.watcher import _start_watcher, _stop_watcher
from gera.repository import Repository

from gera.utils import get_emit

logger = logging.getLogger(__name__)

commands: Commands = Commands()

# Module-level reference to the active data root, set during main()
_data_root: Path | None = None
_repo: Repository | None = None


def get_data_root() -> Path:
    """Return the active data root. Raises if called before init."""
    if _data_root is None:
        raise RuntimeError("Data directory not initialised – call main() first")
    return _data_root


def get_repo() -> Repository:
    """Return the active repository. Raises if called before init."""
    if _repo is None:
        raise RuntimeError("Repository not initialised – call main() first")
    return _repo


# ---------------------------------------------------------------------------
# Tauri commands
# ---------------------------------------------------------------------------


class Person(BaseModel):
    name: str


@commands.command()
async def greet(body: Person) -> str:
    return f"Hello, {body.name}! You've been greeted from Python!"


class DataRootStatus(BaseModel):
    path: str
    structure: dict[str, bool]


@commands.command()
async def get_data_root_status(body: None) -> DataRootStatus:
    """Return the current data root path and its structure health."""
    root = get_data_root()
    return DataRootStatus(
        path=str(root),
        structure=verify_structure(root),
    )


class RenderMarkdownRequest(BaseModel):
    content: str


class RenderMarkdownResponse(BaseModel):
    html: str
    title: str
    frontmatter: dict
    event_ids: list[str]
    project_ids: list[str]


@commands.command()
async def render_markdown_cmd(body: RenderMarkdownRequest) -> RenderMarkdownResponse:
    """Render a Gera markdown document to HTML with Gera-specific syntax."""
    result = render_markdown(body.content)
    return RenderMarkdownResponse(
        html=result.html,
        title=result.title,
        frontmatter=result.frontmatter,
        event_ids=result.event_ids,
        project_ids=result.project_ids,
    )


# --- Entity listing commands ------------------------------------------------


class EventList(BaseModel):
    events: list[EventEntity]
    next_cursor: str | None = None


class PageRequest(BaseModel):
    limit: int = 100
    cursor: str | None = None


class EventListRequest(PageRequest):
    from_: datetime | None = None
    to: datetime | None = None


@commands.command()
async def list_events(body: EventListRequest) -> EventList:
    """Return events with cursor pagination and optional time-range filtering."""
    events, next_cursor = get_repo().list_events_page(
        limit=body.limit,
        cursor=body.cursor,
        from_=body.from_,
        to=body.to,
    )
    return EventList(events=events, next_cursor=next_cursor)


class NoteList(BaseModel):
    notes: list[NoteEntity]
    next_cursor: str | None = None


class NoteListRequest(PageRequest):
    event_id: str | None = None
    project_id: str | None = None


@commands.command()
async def list_notes(body: NoteListRequest) -> NoteList:
    """Return notes with cursor pagination and optional relationship filtering."""
    notes, next_cursor = get_repo().list_notes_page(
        limit=body.limit,
        cursor=body.cursor,
        event_id=body.event_id,
        project_id=body.project_id,
    )
    return NoteList(notes=notes, next_cursor=next_cursor)


class ProjectList(BaseModel):
    projects: list[ProjectEntity]
    next_cursor: str | None = None


@commands.command()
async def list_projects(body: PageRequest) -> ProjectList:
    """Return projects with cursor pagination."""
    projects, next_cursor = get_repo().list_projects_page(
        limit=body.limit,
        cursor=body.cursor,
    )
    return ProjectList(projects=projects, next_cursor=next_cursor)


class TaskList(BaseModel):
    tasks: list[TaskEntity]
    next_cursor: str | None = None


class TaskListRequest(PageRequest):
    deadline_from: datetime | None = None
    deadline_to: datetime | None = None
    event_id: str | None = None
    project_id: str | None = None


@commands.command()
async def list_floating_tasks(body: TaskListRequest) -> TaskList:
    """Return tasks with cursor pagination and optional time/relationship filtering."""
    tasks, next_cursor = get_repo().list_tasks_page(
        limit=body.limit,
        cursor=body.cursor,
        deadline_from=body.deadline_from,
        deadline_to=body.deadline_to,
        event_id=body.event_id,
        project_id=body.project_id,
    )
    return TaskList(tasks=tasks, next_cursor=next_cursor)


class NoteContentRequest(BaseModel):
    filename: str


class NoteContentResponse(BaseModel):
    filename: str
    raw_content: str
    html: str
    title: str
    event_ids: list[str]
    project_ids: list[str]


@commands.command()
async def get_note_content(body: NoteContentRequest) -> NoteContentResponse:
    """Read and render a specific note by filename."""
    from gera.paths import note_file

    path = note_file(get_data_root(), body.filename)
    raw = path.read_text(encoding="utf-8")
    rendered = render_markdown(raw)
    return NoteContentResponse(
        filename=body.filename,
        raw_content=raw,
        html=rendered.html,
        title=rendered.title,
        event_ids=rendered.event_ids,
        project_ids=rendered.project_ids,
    )


# ============================================================================
#   SEARCH COMMANDS - FTS5 Backend Search
# ============================================================================


class SearchRequest(BaseModel):
    query: str


class EventSearchResponse(BaseModel):
    events: list[EventEntity]


@commands.command()
async def search_events(body: SearchRequest) -> EventSearchResponse:
    """Full-text search events using FTS5."""
    events = get_repo().search_events(body.query)
    return EventSearchResponse(events=events)


class NotesSearchResponse(BaseModel):
    notes: list[NoteEntity]


@commands.command()
async def search_notes(body: SearchRequest) -> NotesSearchResponse:
    """Full-text search notes using FTS5."""
    notes = get_repo().search_notes(body.query)
    return NotesSearchResponse(notes=notes)


class ProjectsSearchResponse(BaseModel):
    projects: list[ProjectEntity]


@commands.command()
async def search_projects(body: SearchRequest) -> ProjectsSearchResponse:
    """Full-text search projects using FTS5."""
    projects = get_repo().search_projects(body.query)
    return ProjectsSearchResponse(projects=projects)


class TasksSearchResponse(BaseModel):
    tasks: list[TaskEntity]


@commands.command()
async def search_tasks(body: SearchRequest) -> TasksSearchResponse:
    """Full-text search tasks using FTS5."""
    tasks = get_repo().search_tasks(body.query)
    return TasksSearchResponse(tasks=tasks)


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------


def main() -> int:
    global _data_root  # noqa: PLW0603
    global _repo  # noqa: PLW0603

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialise the data directory (creates dirs/seed files if needed)
    try:
        _data_root = init_data_directory()
        _repo = Repository(_data_root)
        _repo.reload()
        logger.info("Data root: %s", _data_root)
    except Exception:
        logger.exception("Failed to initialise data directory")
        return 1

    with start_blocking_portal("asyncio") as portal:  # or `trio`
        app = builder_factory().build(
            context=context_factory(),
            invoke_handler=commands.generate_handler(portal),
        )

        # Start the file-system watcher (emits gera://fs-changed events)
        handle = app.handle()

        _emit = get_emit(handle)

        # Give Repository the emit function now that app handle exists
        if _repo is not None:
            _repo.set_emit(_emit)

        def _on_fs_changed(event: str, payload: str) -> None:
            """Handle file-system changes: reload affected tables.

            The repository emits ``gera://data-changed`` itself after reload.
            """
            if _repo is not None:
                try:
                    data = json.loads(payload)
                    paths = [c["path"] for c in data.get("changes", [])]
                    _repo.reload_for_changes(paths)
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Malformed fs-changed payload, doing full reload")
                    _repo.reload()
                    _repo.emit_data_changed(
                        [{"entity": t, "ids": None} for t in ["events", "notes", "projects", "tasks"]]
                    )

        watcher_handle = _start_watcher(_data_root, _on_fs_changed)

        exit_code = app.run_return()

        # Clean up
        _stop_watcher(watcher_handle)
        if _repo is not None:
            _repo.close()

        return exit_code
