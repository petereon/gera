import json
import logging
from datetime import datetime
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic import BaseModel
from pytauri import (
    AppHandle,
    Commands,
    Manager,
    builder_factory,
    context_factory,
)

from gera.entities import (
    EventEntity,
    NoteEntity,
    ProjectEntity,
    TaskEntity,
)
from gera.entities.event_metadata import EventMetadata
from gera.filesystem import init_data_directory, verify_structure
from gera.renderer import render as render_markdown
from gera.repository import VAULT_CHANGED_EVENT, Repository
from gera.utils import get_emit
from gera.watcher import _start_watcher, _stop_watcher

logger = logging.getLogger(__name__)

commands: Commands = Commands()

# Module-level reference to the active data root, set during main()
_data_root: Path | None = None
_repo: Repository | None = None
_watcher_handle = None
_emit_fn = None  # callable(event, payload) once app handle is available
_app_data_dir: Path | None = None  # Tauri app-data dir, set once after build()


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


class UpdateNoteContentRequest(BaseModel):
    filename: str
    content: str


@commands.command()
async def update_note_content(body: UpdateNoteContentRequest) -> None:
    """Update a note file with new markdown content."""
    get_repo().update_note(body.filename, body.content)


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


# ============================================================================
#   TASK MUTATION COMMANDS
# ============================================================================


class ToggleTaskRequest(BaseModel):
    source_file: str
    line_number: int


@commands.command()
async def toggle_task(body: ToggleTaskRequest) -> None:
    """Toggle a task's completion status in its source markdown file."""
    from gera.service import tasks

    tasks.toggle_task(get_repo(), body.source_file, body.line_number)


class CreateTaskRequest(BaseModel):
    text: str


class CreateTaskResponse(BaseModel):
    task: TaskEntity


@commands.command()
async def create_task(body: CreateTaskRequest) -> CreateTaskResponse:
    """Create a new floating task in tasks.md."""
    from gera.service import tasks

    task = tasks.create_task(get_repo(), body.text)
    return CreateTaskResponse(task=task)


class CreateNoteRequest(BaseModel):
    filename: str
    content: str = ""
    event_ids: list[str] | None = None
    project_ids: list[str] | None = None


class CreateNoteResponse(BaseModel):
    note: NoteEntity


@commands.command()
async def create_note(body: CreateNoteRequest) -> CreateNoteResponse:
    """Create a new note file."""
    from gera.service import notes

    note = notes.create_note(
        get_repo(),
        body.filename,
        body.content,
        event_ids=body.event_ids,
        project_ids=body.project_ids,
    )
    return CreateNoteResponse(note=note)


class UpdateTaskRequest(BaseModel):
    source_file: str
    line_number: int
    new_text: str


@commands.command()
async def update_task(body: UpdateTaskRequest) -> None:
    """Update the text of an existing task."""
    from gera.service import tasks

    tasks.update_task(get_repo(), body.source_file, body.line_number, body.new_text)


class DeleteTaskRequest(BaseModel):
    source_file: str
    line_number: int


@commands.command()
async def delete_task(body: DeleteTaskRequest) -> None:
    """Delete a task line from its source file."""
    from gera.service import tasks

    tasks.delete_task(get_repo(), body.source_file, body.line_number)


class DeleteNoteRequest(BaseModel):
    filename: str


@commands.command()
async def delete_note(body: DeleteNoteRequest) -> None:
    """Delete a note file."""
    from gera.service import notes

    notes.delete_note(get_repo(), body.filename)


# ============================================================================
#   EVENT MUTATION COMMANDS
# ============================================================================


class CreateEventRequest(BaseModel):
    id: str
    source: str = "local"
    from_: datetime
    to: datetime
    name: str
    description: str = ""
    participants: list[str] = []
    location: str = ""
    metadata: dict | None = None


class CreateEventResponse(BaseModel):
    event: EventEntity


@commands.command()
async def create_event(body: CreateEventRequest) -> CreateEventResponse:
    """Create a new event and append it to events.yaml."""
    # Normalize incoming metadata into the EventMetadata model so EventEntity
    # receives the correct typed value (Pydantic v2 model).
    if isinstance(body.metadata, EventMetadata):
        metadata_val = body.metadata
    elif body.metadata is None:
        metadata_val = EventMetadata()
    else:
        metadata_val = EventMetadata.model_validate(body.metadata)

    ev = EventEntity(
        id=body.id,
        source=body.source,
        from_=body.from_,
        to=body.to,
        name=body.name,
        description=body.description,
        participants=body.participants,
        location=body.location,
        metadata=metadata_val,
    )
    result = get_repo().create_event(ev)
    return CreateEventResponse(event=result)


class UpdateEventRequest(BaseModel):
    id: str
    name: str
    from_: datetime
    to: datetime
    description: str = ""
    location: str = ""
    participants: list[str] = []


class UpdateEventResponse(BaseModel):
    event: EventEntity


@commands.command()
async def update_event(body: UpdateEventRequest) -> UpdateEventResponse:
    """Update an existing event in events.yaml."""
    event = get_repo().get_event(body.id)
    if event is None:
        raise KeyError(f"Event not found: {body.id}")

    updated = EventEntity(
        id=event.id,
        source=event.source,
        from_=body.from_,
        to=body.to,
        name=body.name,
        description=body.description,
        location=body.location,
        participants=body.participants,
    )
    result = get_repo().update_event(updated)
    return UpdateEventResponse(event=result)


class DeleteEventRequest(BaseModel):
    id: str


@commands.command()
async def delete_event(body: DeleteEventRequest) -> None:
    """Delete an event from events.yaml."""
    get_repo().delete_event(body.id)


# ============================================================================
#   GOOGLE CALENDAR SYNC
# ============================================================================


class SyncGoogleCalendarRequest(BaseModel):
    account_email: str
    calendar_id: str = "primary"


class SyncGoogleCalendarResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    stale: int


@commands.command()
async def sync_google_calendar(
    body: SyncGoogleCalendarRequest, app_handle: AppHandle
) -> SyncGoogleCalendarResponse:
    """Fetch and merge events from a connected Google Calendar account.

    Args:
        account_email: Email of the connected Google account
        calendar_id: Google Calendar ID to sync (default 'primary')

    Returns:
        Sync result with counts of created/updated/skipped/stale events

    Note:
        Google tokens are stored in the Tauri app data directory by the Rust OAuth handler.
    """
    from gera.service import google_calendar

    token_file = Manager.path(app_handle).app_data_dir() / "google_tokens.json"
    if not token_file.exists():
        raise ValueError(
            f"No Google tokens found at {token_file}. Please authenticate first."
        )

    try:
        tokens_data = json.loads(token_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Failed to read Google tokens: {e}") from e

    # Find token for this account email
    token_data = None
    for token in tokens_data:
        if token.get("account_email") == body.account_email:
            token_data = token
            break

    if token_data is None:
        raise ValueError(f"No token found for account: {body.account_email}")

    # Refresh the access token (expires after ~1 hour) before calling the API.
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            f"No refresh token stored for {body.account_email}. Re-authenticate."
        )
    try:
        refreshed = google_calendar.refresh_access_token(refresh_token)
    except ValueError as exc:
        raise ValueError(f"Could not refresh Google token: {exc}") from exc
    # Update the in-memory record and persist the new access token.
    token_data = {**token_data, **refreshed}
    for i, tok in enumerate(tokens_data):
        if tok.get("account_email") == body.account_email:
            tokens_data[i] = token_data
            break
    try:
        token_file.write_text(json.dumps(tokens_data, indent=2), encoding="utf-8")
    except IOError as exc:
        logger.warning("Failed to persist refreshed token: %s", exc)

    # Perform sync
    result = google_calendar.sync_google_events(
        repo=get_repo(),
        access_token=token_data["access_token"],
        account_email=body.account_email,
        calendar_id=body.calendar_id,
    )

    return SyncGoogleCalendarResponse(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        stale=result.stale,
    )


# ---------------------------------------------------------------------------
# Vault management helpers
# ---------------------------------------------------------------------------


def _get_app_data_dir() -> Path | None:
    """Return the resolved Tauri app-data directory, or None if not yet set."""
    return _app_data_dir


def _load_recent_vaults() -> list[str]:
    adir = _get_app_data_dir()
    if adir is None:
        return []
    vaults_file = adir / "vaults.json"
    if not vaults_file.exists():
        return []
    try:
        data = json.loads(vaults_file.read_text(encoding="utf-8"))
        return data.get("recent", [])
    except Exception:
        return []


def _save_recent_vault(path: str) -> None:
    adir = _get_app_data_dir()
    adir.mkdir(parents=True, exist_ok=True)
    if adir is None:
        return
    vaults_file = adir / "vaults.json"
    recent = _load_recent_vaults()
    recent = [p for p in recent if p != path]
    recent.insert(0, path)
    vaults_file.write_text(
        json.dumps({"recent": recent[:10]}, indent=2), encoding="utf-8"
    )


def _on_fs_changed(event: str, payload: str) -> None:
    """Handle file-system changes: reload affected tables."""
    if _repo is not None:
        try:
            data = json.loads(payload)
            paths = [c["path"] for c in data.get("changes", [])]
            _repo.reload_for_changes(paths)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Malformed fs-changed payload, doing full reload")
            _repo.reload()
            _repo.emit_data_changed(
                [
                    {"entity": t, "ids": None}
                    for t in ["events", "notes", "projects", "tasks"]
                ]
            )


def _resolve_startup_vault() -> Path:
    """Return the vault path to open at startup.

    Priority:
    1. Most-recently-used vault recorded in ``vaults.json``
       — only if the path still exists and passes structure validation.
    2. Default data root (``~/Documents/Gera``), initialised if needed.
    """
    recent = _load_recent_vaults()
    if recent:
        candidate = Path(recent[0])
        structure = verify_structure(candidate)
        if (
            structure.get(".")
            and structure.get("events.yaml")
            and structure.get("tasks.md")
        ):
            logger.info("Resuming last vault: %s", candidate)
            return candidate
        logger.warning(
            "Last vault no longer valid, falling back to default: %s", candidate
        )
    return init_data_directory()


def _switch_vault(new_path: Path, *, initialize: bool) -> None:
    """Switch the active vault to *new_path*.

    If *initialize* is True, calls init_data_directory() to create the vault
    structure.  Otherwise, calls verify_structure() and raises ValueError if the
    directory is not a valid Gera vault.
    """
    global _data_root, _repo, _watcher_handle  # noqa: PLW0603

    if initialize:
        resolved = init_data_directory(new_path)
    else:
        resolved = new_path.expanduser().resolve()
        structure = verify_structure(resolved)
        if (
            not structure.get(".")
            or not structure.get("events.yaml")
            or not structure.get("tasks.md")
        ):
            raise ValueError(f"Not a valid Gera vault: {resolved}")

    # Stop the current watcher; drop the old repo reference (SQLite closes via GC —
    # calling close() from a different thread raises ProgrammingError).
    if _watcher_handle is not None:
        _stop_watcher(_watcher_handle)
        _watcher_handle = None
    _repo = None  # drop reference; connection closed by GC on the owning thread

    # Signal the UI to clear its state and show a loading indicator.
    if _emit_fn is not None:
        try:
            _emit_fn(VAULT_CHANGED_EVENT, json.dumps({"path": str(resolved)}))
        except Exception:
            logger.exception("Failed to emit %s", VAULT_CHANGED_EVENT)

    _data_root = resolved
    _repo = Repository(_data_root)
    _repo.clear_all()  # unconditionally wipe shared in-memory DB before loading new vault
    _repo.reload()

    if _emit_fn is not None:
        _repo.set_emit(_emit_fn)

    _watcher_handle = _start_watcher(_data_root, _on_fs_changed)

    _repo.emit_data_changed(
        [{"entity": t, "ids": None} for t in ["events", "notes", "projects", "tasks"]]
    )

    logger.info("Switched vault to: %s", _data_root)


# ---------------------------------------------------------------------------
# Vault Tauri commands
# ---------------------------------------------------------------------------


class VaultInfo(BaseModel):
    path: str
    name: str


class VaultStatus(BaseModel):
    current: str
    recent: list[VaultInfo]


@commands.command()
async def get_vault_status(body: None) -> VaultStatus:
    """Return the current vault path and the list of recently opened vaults."""
    return VaultStatus(
        current=str(_data_root) if _data_root else "",
        recent=[VaultInfo(path=p, name=Path(p).name) for p in _load_recent_vaults()],
    )


class VaultPathRequest(BaseModel):
    path: str


@commands.command()
async def new_vault(body: VaultPathRequest) -> VaultStatus:
    """Initialize a new Gera vault at *path* and switch to it."""
    _switch_vault(Path(body.path), initialize=True)
    _save_recent_vault(str(_data_root))
    return await get_vault_status(None)


@commands.command()
async def open_vault(body: VaultPathRequest) -> VaultStatus:
    """Open an existing Gera vault at *path* and switch to it."""
    _switch_vault(Path(body.path), initialize=False)
    _save_recent_vault(str(_data_root))
    return await get_vault_status(None)


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------


def main() -> int:
    global _data_root  # noqa: PLW0603
    global _repo  # noqa: PLW0603
    global _watcher_handle  # noqa: PLW0603
    global _emit_fn  # noqa: PLW0603
    global _app_data_dir  # noqa: PLW0603

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with start_blocking_portal("asyncio") as portal:  # or `trio`
        app = builder_factory().build(
            context=context_factory(),
            invoke_handler=commands.generate_handler(portal),
        )

        handle = app.handle()
        _emit_fn = get_emit(handle)
        # Use the same path resolver as commands so reads and writes go to the
        # same vaults.json regardless of how the OS propagates env vars.
        _app_data_dir = Manager.path(handle).app_data_dir()
        logger.info("App data dir: %s", _app_data_dir)

        try:
            _data_root = _resolve_startup_vault()
            _repo = Repository(_data_root)
            _repo.reload()
            _repo.set_emit(_emit_fn)
            logger.info("Data root: %s", _data_root)
            # Persist so next launch reopens this vault.
            _save_recent_vault(str(_data_root))
        except Exception:
            logger.exception("Failed to initialise data directory")
            return 1

        _watcher_handle = _start_watcher(_data_root, _on_fs_changed)

        exit_code = app.run_return()

        # _repo.close() intentionally omitted: the SQLite keep-alive was created
        # on a different thread; calling close() here raises ProgrammingError.
        # The in-memory DB is freed automatically when the process exits.
        if _watcher_handle is not None:
            _stop_watcher(_watcher_handle)

        return exit_code
