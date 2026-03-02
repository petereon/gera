# Gera — Agent Guidelines

## 1. Data Flow — The Golden Rule

```
                              ┌─────────────────────────────┐
Files on disk  ◀──(writers)──▶│  Repository (SQLite)        │──(Tauri commands)──▶  Frontend (React)
     │           (loaders)    │                             │                            │
     │                        │  emit gera://data-changed ─┼──────────────────────────▶ │
     │                        │  (entity types + IDs)       │                            │
     │                        └─────────────────────────────┘                            │
     │                                     ▲                                             │
     │                                     └──────(Tauri commands)───────────────────────┘
     │
     └── file watcher ──▶ reload_for_changes()
```

### Reading (pull model)
- **Repository is the single source of truth for the UI.** The frontend never reads files directly.
- **Repository is only ever populated from files.** Service loaders parse the filesystem; their output is INSERT-ed into the in-memory SQLite database.
- The frontend calls Tauri commands (e.g. `list_events`, `search_notes`) which query the Repository and return entities.

### Writing
- **The frontend initiates all mutations** by calling Tauri commands that delegate to Repository write methods.
- **Repository write methods write to files first**, then reload the affected entity type from disk, then emit `gera://data-changed`.
- The file watcher catches external edits (e.g. user editing in VS Code) and triggers the same granular reload path.
- **Never INSERT/UPDATE the SQLite tables directly in write methods.** All data enters the Repository through the `reload_*()` methods which read from disk. Write methods only touch files, then call `reload_*()`.

### Notification (push model)
- After any reload (whether from a backend write or an external file change), the backend **emits a Tauri event** telling the frontend *which entity types and IDs* were updated.
- The frontend listens for this event and **re-fetches only the affected data** via the normal query commands (`list_*`, `get_*`, `search_*`).
- The backend never pushes full entity data in the event payload — it only signals *what* changed. The frontend pulls the fresh data.
- Payload shape: `{"changes": [{"entity": "events", "ids": ["event-1", "event-2"]}, {"entity": "notes", "ids": ["meeting-notes.md"]}, ...]}`. When IDs cannot be determined (e.g. full reload), `ids` is `null` meaning "all of this type changed".
- This keeps the frontend reactive without polling: write → file change → reload repository → emit notification → frontend pulls.

### Summary
| Direction | Mechanism |
|---|---|
| Disk → Repository | `reload_events()`, `reload_notes()`, `reload_projects()`, `reload_tasks()` via service loaders |
| Repository → Frontend (query) | Tauri commands that query SQLite and return Pydantic entities |
| Repository → Frontend (notify) | Tauri event `gera://data-changed` with `{"changes": [{"entity": "events", "ids": [...]}, ...]}` |
| Frontend → Disk | Tauri commands → Repository write methods → file I/O → reload affected table |
| External edit → Repository | File watcher emits `gera://fs-changed`, `_on_fs_changed` calls `reload_for_changes()` then emits `gera://data-changed` |

---

## 2. Project Structure

```
src-tauri/src-python/gera/
├── __init__.py          # Re-exports main() only
├── app.py               # Entry point: Tauri commands + main()
├── repository.py         # In-memory SQLite (shared cache), all queries and FTS
├── entities/             # Pure Pydantic v2 models (no logic)
│   ├── event.py
│   ├── note.py
│   ├── project.py
│   └── task.py
├── service/              # File-system loaders (read-only, parse files → entities)
│   ├── events.py
│   ├── notes.py
│   ├── projects.py
│   ├── tasks.py
│   └── _helpers.py
├── watcher.py            # watchfiles daemon, emits gera://fs-changed
├── filesystem.py         # Directory structure verification
├── frontmatter.py        # YAML frontmatter parsing
├── renderer.py           # Markdown → HTML rendering
├── paths.py              # Path constants and resolvers
├── utils.py              # Shared utilities
└── errors.py             # Custom exception types
```

### Module responsibilities
- **`entities/`** — Pure data classes. No imports from other gera modules. No file I/O.
- **`service/`** — Each module has a `load_*()` function that reads from `data_root` and returns a list of entities. Read-only. No SQLite.
- **`repository.py`** — Owns the SQLite connection and all file I/O. Calls service loaders inside `reload_*()`. Exposes query methods (`list_*`, `get_*`, `search_*`) and write methods that persist to disk then reload.
- **`app.py`** — Thin command layer. Each `@Commands` function delegates to `_repo`. Holds `_data_root` and `_repo` as module globals. Sets up watcher and lifecycle.

---

## 3. Repository Conventions

### SQLite setup
- URI: `file::memory:?cache=shared` — all connections share the same in-memory database.
- A **keep-alive connection** (`self._keepalive`) is held open for the lifetime of the app to prevent the shared-cache DB from being garbage-collected.
- `self._conn()` returns a fresh connection with `row_factory = sqlite3.Row` for each operation.
- `PRAGMA journal_mode=WAL` is set on the keep-alive connection.

### Schema
- Regular tables: `events`, `notes`, `projects`, `tasks`.
- FTS5 virtual tables: `events_fts`, `notes_fts`, `projects_fts`, `tasks_fts` — external content tables pointing back to their parent table via `content=` and `content_rowid=`.
- JSON arrays (e.g. `event_ids`, `project_ids`, `participants`) are stored as TEXT containing JSON. Use `json.loads()` on read, `json.dumps()` on write.

### Reload pattern
Each `reload_<entity>()` method follows the same pattern:
1. Call the corresponding service loader to get entities from disk.
2. `DELETE FROM <table>` and `DELETE FROM <table>_fts`.
3. `INSERT` all entities into the main table.
4. Populate the FTS table from the main table.
5. `COMMIT`.

### Granular reload
- `reload_for_changes(changed_paths)` maps file paths to entity types and calls only the relevant `reload_*()` methods.
- `reload()` calls all four reload methods (used at startup).

### Write pattern
Repository write methods (e.g. `create_note()`, `update_note()`, `toggle_task()`) follow this pattern:
1. Validate input.
2. Write/update the file on disk (YAML for events, Markdown for notes/projects/tasks).
3. Call the corresponding `reload_*()` to re-read from disk into SQLite.
4. Emit `gera://data-changed` with the affected entity type and IDs.
5. Return the created/updated entity.

This ensures SQLite is never out of sync with disk — writes always round-trip through files.

---

## 4. Tauri Command Conventions

### IPC rules
- Commands are registered via PyTauri's `Commands` and `builder_factory`.
- Commands that take no body payload must still receive `body: None` — the frontend must pass explicit `null`.
- Commands return Pydantic models (or lists thereof); serialization is automatic.
- Commands should be thin: validate input, delegate to `_repo` or a service function, return result.

### Naming
- Query commands: `list_<entity>s`, `get_<entity>`, `search_<entity>s`
- Mutation commands: `create_<entity>`, `update_<entity>`, `delete_<entity>`, `toggle_task` — these delegate to Repository write methods

---

## 5. Entity Design

- All entities are **Pydantic v2 `BaseModel`** subclasses.
- Field naming follows Python convention (`snake_case`). Use `alias` for serialization if needed.
- `TaskEntity` is virtual — it has no file of its own. It is parsed from `- [ ]` lines inside notes, projects, or `tasks.md`.
- `line_number` on `TaskEntity` exists for write-back: to update a specific line in the source markdown file.
- Inheritance rule: when a task is inside a note/project, it **merges** (not overrides) the parent's `event_ids` and `project_ids` with its own inline references.

---

## 6. File Watcher

- Uses `watchfiles` library in a daemon thread.
- Debounce: 300ms.
- Emits `gera://fs-changed` Tauri event with payload: `{"changes": [{"type": "modified", "path": "relative/path"}, ...]}`.
- `_on_fs_changed` in `app.py` parses this payload and calls `_repo.reload_for_changes()`.

---

## 7. Code Style & Tooling

- **Formatter/linter:** `ruff check --fix .` — always run after changes.
- **Python version:** 3.12+ (match PyTauri requirements).
- **Type hints:** Required on all public functions and method signatures.
- **Logging:** Use `logging.getLogger(__name__)` per module. Log at INFO for reload operations, DEBUG for queries.
- **No `print()` statements.** Use logger.
- **Imports:** Absolute imports from `gera.*`. No relative imports.

---

## 8. Frontend Conventions

- **React 18 + TypeScript**, bundled with Vite + Bun.
- **"Floating Islands" design:** White panels (`rounded-3xl`, `shadow-md`) over soft gray background (`#F5F7FA`).
- **3-pane layout:** Left (260px staging), Center (flex calendar/editor), Right (320px inspector).
- The frontend calls Python backend via `pyInvoke` and reacts to Tauri events for live updates.
- Tauri events (e.g. `gera://fs-changed`) can be listened to for triggering UI refreshes after file changes.

---

## 9. General Principles

1. **Don't edit code files unless asked.** When the user says "don't edit code", respect it absolutely.
2. **Incremental changes.** Make small, verifiable edits. Don't refactor broadly unless requested.
3. **Backward compatibility.** When changing a function signature, find and update all callers (use `find_referencing_symbols` or grep).
4. **No orphaned files.** Don't create files that aren't integrated into the codebase.
5. **Verify after editing.** Run `ruff check --fix .` after Python changes. Check for compile errors after Rust/TS changes.
6. **Ask before large refactors.** If a request implies restructuring multiple modules, confirm the scope first.