# Gera — Copilot Instructions

## Use the correct directory

/Users/petervyboch/Projects/gera

## Architecture Overview

Gera is a **Tauri v2 + PyTauri** desktop productivity app: Rust shell → Python backend → React/TypeScript frontend.

```
Frontend (React/TS)  ──pyInvoke──▶  Python backend (PyTauri)  ──file I/O──▶  ~/Documents/Gera/
       ▲                                    │
       └────── Tauri events ◀───────────────┘
```

**Key directories:**
- `src/` — React 18 + TypeScript frontend (Vite + Bun)
- `src-tauri/src-python/gera/` — Python backend (the bulk of the logic)
- `src-tauri/src/` — Rust glue (minimal — just PyTauri module init)

## Data Flow — The Golden Rule

**All data enters Repository through `reload_*()` methods that read from disk. Never INSERT into SQLite directly.**

- **Read path:** Files on disk → `Repository._read_*_from_disk()` → SQLite → Tauri commands → Frontend
- **Write path:** Frontend → Tauri command → `Repository.create_*/update_*/delete_*()` → write file → `reload_*()` → emit `gera://data-changed` → Frontend re-fetches
- **External edits:** File watcher → `reload_for_changes(paths)` → emit `gera://data-changed`

The event payload is `{"changes": [{"entity": "events", "ids": ["id1"]}]}` — the frontend pulls fresh data, the backend never pushes full entities.

## Python Backend Structure (`src-tauri/src-python/gera/`)

| Module | Responsibility |
|---|---|
| `app.py` | Tauri `@commands.command()` handlers + `main()` lifecycle. Thin — delegates to Repository or services |
| `repository.py` | **Single source of truth.** In-memory SQLite (`file::memory:?cache=shared`), all file I/O, reload, FTS5 search, write methods, emit |
| `entities/` | Pure Pydantic v2 models. No imports from other gera modules, no I/O |
| `service/` | Domain operations layer. Functions take `repo: Repository`, orchestrate business logic. No direct file I/O |
| `renderer.py` | Markdown→HTML via mistune v3 + Gera post-processing (`@event-id`, `#project-id` → semantic `<span>` elements) |
| `frontmatter.py` | YAML frontmatter parse/serialize for markdown files |
| `paths.py` | Path constants and builders for the data directory |
| `watcher.py` | `watchfiles` daemon thread (300ms debounce), emits `gera://fs-changed` |
| `utils.py` | `get_emit(handle)` wrapper, `body_preview()` |

## Repository Patterns

- SQLite URI: `file::memory:?cache=shared` with a keep-alive connection to prevent GC
- JSON arrays (`event_ids`, `participants`) stored as TEXT — use `json.loads()`/`json.dumps()`
- FTS5 external content tables: `events_fts`, `notes_fts`, `projects_fts`, `tasks_fts`
- Write methods follow: **validate → write file → `reload_*()` → `_emit_data_changed()` → return entity**
- `TaskEntity` is virtual — parsed from `- [ ]` lines in markdown files, has `source_file` + `line_number` for write-back

## Tauri Command Conventions

- Registered via PyTauri's `Commands` + `builder_factory` in `app.py`
- Commands taking no body: `body: None` (frontend must pass explicit `null`)
- Return Pydantic models (auto-serialised). Wrap lists: `EventList(events=...)`, not bare `list[EventEntity]`
- Frontend calls via `pyInvoke` from `src/api.ts` — all backend types are mirrored there

## Frontend Patterns

- **"Floating Islands" design:** White panels (`rounded-3xl`, `shadow-md`) on `#F5F7FA` background
- **3-pane layout:** Left staging (260px), Center calendar/editor (flex), Right inspector (320px)
- `src/api.ts` is the single IPC boundary — all `pyInvoke` calls live there
- Listens to `gera://data-changed` (or currently `gera://fs-changed`) to trigger re-fetches

## Data Directory (`~/Documents/Gera/`)

```
events.yaml          # All events in one YAML file
tasks.md             # Floating tasks (- [ ] / - [x] lines)
notes/*.md           # Markdown notes with YAML frontmatter (event_ids, project_ids)
projects/*.md        # Markdown projects with YAML frontmatter (event_ids)
```

Gera-specific inline syntax in markdown: `@event-id`, `@2026-03-03T18:00`, `@before[2d]:event-id`, `#project-id`

## Dev Workflow

```sh
# Prerequisites: Rust toolchain, Bun, Python 3.12+ venv activated
cd src-tauri && source .venv/bin/activate  # activate Python venv first
bun tauri dev                               # runs both frontend (Vite :1420) and Tauri backend

# Lint Python
ruff check --fix src-tauri/src-python/

# Build standalone
scripts/macos/download-py.sh   # first time only
scripts/macos/build.sh
```

**Always run `ruff check --fix .` after Python changes.** No `print()` — use `logging.getLogger(__name__)`.

## Code Style

- Python: absolute imports (`from gera.entities import ...`), type hints on all public signatures, Pydantic v2 models
- TypeScript: interfaces mirror Python entities in `src/api.ts`
- Entity field naming: `snake_case` in Python, aliased for serialisation where needed (`from_` for the `from` keyword)
