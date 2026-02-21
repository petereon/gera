import logging
from pathlib import Path

from anyio.from_thread import start_blocking_portal
from pydantic import BaseModel
from pytauri import (
    Commands,
    builder_factory,
    context_factory,
)

from pytauri import Emitter

from gera.filesystem import init_data_directory, verify_structure
from gera.renderer import render as render_markdown
from gera.watcher import _start_watcher
from gera.entities import (
    EventEntity,
    NoteEntity,
    ProjectEntity,
    TaskEntity,
    load_events,
    load_notes,
    load_projects,
    load_floating_tasks,
)

logger = logging.getLogger(__name__)

commands: Commands = Commands()

# Module-level reference to the active data root, set during main()
_data_root: Path | None = None


def get_data_root() -> Path:
    """Return the active data root. Raises if called before init."""
    if _data_root is None:
        raise RuntimeError("Data directory not initialised – call main() first")
    return _data_root


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


@commands.command()
async def list_events(body: None) -> EventList:
    """Return all events from events.yaml."""
    return EventList(events=load_events(get_data_root()))


class NoteList(BaseModel):
    notes: list[NoteEntity]


@commands.command()
async def list_notes(body: None) -> NoteList:
    """Return all notes from notes/."""
    return NoteList(notes=load_notes(get_data_root()))


class ProjectList(BaseModel):
    projects: list[ProjectEntity]


@commands.command()
async def list_projects(body: None) -> ProjectList:
    """Return all projects from projects/."""
    return ProjectList(projects=load_projects(get_data_root()))


class TaskList(BaseModel):
    tasks: list[TaskEntity]


@commands.command()
async def list_floating_tasks(body: None) -> TaskList:
    """Return all floating tasks from tasks.md."""
    return TaskList(tasks=load_floating_tasks(get_data_root()))


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


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------


def main() -> int:
    global _data_root  # noqa: PLW0603

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialise the data directory (creates dirs/seed files if needed)
    try:
        _data_root = init_data_directory()
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

        def _emit(event: str, payload: str) -> None:
            Emitter.emit_str(handle, event, payload)

        _start_watcher(_data_root, _emit)

        exit_code = app.run_return()
        return exit_code