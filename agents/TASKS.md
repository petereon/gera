# Gera - Task Breakdown

## Legend
- `[frontend]` - React/TypeScript UI work
- `[backend]` - Rust/Python Tauri backend work  
- `[both]` - Requires coordination between frontend and backend
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Complete

---

## Phase 1: Foundation & Persistence Layer

### 1.1 File System Setup `[backend]`
- [x] Create default directory structure on first launch (`events.yaml`, `tasks.md`, `/notes/`, `/projects/`)
- [x] Implement file path utilities and constants (base data dir, subdirectory resolvers)
- [x] Validate directory structure exists on startup, create missing dirs
- [x] Add error handling for file I/O operations (permissions, disk full, etc.)

### 1.2 Markdown Parser `[backend]`
- [x] Implement YAML frontmatter parser (for notes/projects)
- [x] Implement YAML frontmatter writer/updater
- [x] Parse Markdown body content
- [x] Extract tasks (`- [ ]` / `- [x]`) from Markdown content
- [x] Parse task references: `@event-id`, `@before[2d]:event-id`, `@2026-3-3T18:00`
- [x] Parse project tags: `#project-id`
- [x] Parse time offset units (Y, M, W, D, h, m - case sensitive)
- [ ] Implement inheritance merge logic (note/project → task)

### 1.3 Entity Models `[backend]`
- [x] Event model: `id`, `source`, `from`, `to`, `name`, `description`, `participants`
- [x] Note model: Markdown with YAML preamble (`event_ids`, `project_ids`), title from H1 or first words
- [x] Project model: Markdown with YAML preamble (`event_ids`), ID = filename, no deadline
- [ ] Task model (virtual): parsed from `- [ ]` lines, with `@event`, `@before[offset]:event`, `@datetime`, `#project`
- [ ] Implement merge semantics: tasks inherit from parent note/project, merge (not override)

### 1.4 Implement Calendar import `[backend]`
- [ ] Implement import from different calendar backends
    - [ ] Gmail
    - [ ] Outlook
    - [ ] Apple

### 1.5 File CRUD Operations `[backend]`
- [ ] Create new Event entry (`/events/<id>.yaml`)
- [ ] Create new Note file (`/notes/<name>.md`) with YAML frontmatter
- [ ] Create new Project file (`/projects/<name>.md`) with YAML frontmatter
- [ ] Read and parse existing files (YAML events, Markdown notes/projects)
- [ ] Update file content and frontmatter
- [ ] Delete/archive files

---

## Phase 2: State Management & Indexer

### 2.1 In-Memory Index `[backend]`
- [ ] Design index data structure (events by date, notes, tasks)
- [ ] Implement startup indexer that parses all YAML headers
- [ ] Build query methods (get events by date range, get all floating notes, etc.)
- [ ] Optimize for calendar grid rendering

### 2.2 File Watcher `[backend]`
- [ ] Set up file system watcher for `/events/`, `/notes/`, `/projects/`
- [ ] Handle App → File sync (UI changes write to disk immediately)
- [ ] Handle File → App sync (external edits trigger index hot-reload)
- [ ] Debounce rapid file changes
- [ ] Handle file rename/move detection

### 2.3 IPC Bridge `[both]`
- [ ] Define Tauri commands for CRUD operations
- [ ] Define Tauri commands for index queries
- [ ] Implement event system for file change notifications to frontend
- [ ] Type-safe API contracts between frontend and backend

---

## Phase 3: Core UI Components

### 3.1 Layout Shell `[frontend]`
- [x] 3-pane grid layout (Left 260px, Center flex, Right 320px)
- [x] Island pane base component with shadows
- [ ] Collapsible panes (Focus Mode)
- [ ] Responsive behavior / minimum widths

### 3.2 Left Pane - Staging Area `[frontend]`
- [x] Navigation icons (Inbox, Today, Projects, Tags)
- [x] Floating Notes list with draggable cards
- [x] Quick Capture input field
- [ ] Badge counts (unread inbox items)
- [ ] Filter/sort options for notes

### 3.3 Center Pane - Calendar Grid `[frontend]`
- [x] Week view with day headers
- [x] Time slots (hourly grid)
- [x] Event blocks with basic styling
- [ ] Day view mode
- [ ] Month view mode
- [ ] View toggle functionality (Day/Week/Month)
- [ ] Navigate between weeks/months
- [ ] Today highlight
- [ ] Current time indicator line

### 3.4 Right Pane - Context Inspector `[frontend]`
- [x] Selected event details display
- [x] Linked Tasks section
- [x] Action buttons (Join Video Call, Edit)
- [ ] Attendees management
- [ ] Event metadata editing
- [ ] "Last Week's Open Tasks" for recurring events

### 3.5 Event Block Component `[frontend]`
- [x] Basic event block styling
- [x] Ghost/preview state for dragging
- [ ] Multi-day event spanning
- [ ] Overlapping events handling
- [ ] Resize handles for duration adjustment
- [ ] Color coding by type/tag

---

## Phase 4: User Flow - Quick Capture

### 4.1 Capture Input `[frontend]`
- [x] Input field UI in Left Pane
- [ ] Submit on Enter key
- [ ] Clear input after submission
- [ ] Loading/success feedback

### 4.2 Capture Backend `[backend]`
- [ ] Tauri command: `create_quick_note(content: string)`
- [ ] Generate UUID and timestamp
- [ ] Create file in `/notes/inbox/`
- [ ] Return new note entity to frontend

### 4.3 Global Hotkey `[both]`
- [ ] Register global hotkey (e.g., Cmd+Shift+N)
- [ ] Open quick capture modal/popover
- [ ] Focus input automatically

---

## Phase 5: User Flow - Anchoring (Drag & Drop)

### 5.1 Drag Source `[frontend]`
- [x] Make note cards draggable
- [x] Visual feedback on drag start (opacity change)
- [ ] Drag data transfer (note ID)
- [ ] Remove from list on successful drop

### 5.2 Drop Target - Calendar `[frontend]`
- [ ] Calendar cells as drop zones
- [ ] Ghost event preview on hover (snap to 15-min grid)
- [ ] Visual highlight of target time slot
- [ ] Calculate drop time from mouse position

### 5.3 Anchoring Backend `[backend]`
- [ ] Tauri command: `anchor_note(note_id: string, from: datetime, to: datetime)`
- [ ] Create event entry in `/events/<id>.yaml` with `from`/`to`
- [ ] Add event ID to note's `event_ids` frontmatter
- [ ] Update index

### 5.4 Integration `[both]`
- [ ] Frontend calls backend on drop
- [ ] Refresh calendar view after anchor
- [ ] Update Left Pane to remove anchored note
- [ ] Handle undo/revert

---

## Phase 6: User Flow - Deep Work (Document Editor)

### 6.1 Editor View `[frontend]`
- [ ] Center Pane transforms to Document Editor on event click
- [ ] Back button to return to Calendar
- [ ] Full-width Markdown editor
- [ ] Live preview or split view option

### 6.2 Markdown Editor `[frontend]`
- [ ] Rich text editing (headings, bold, italic, links)
- [ ] Code block support
- [ ] Checkbox/task list rendering (`- [ ]`)
- [ ] Toggle checkbox on click
- [ ] Auto-save indicator

### 6.3 Editor Backend `[backend]`
- [ ] Tauri command: `get_event_content(event_id: string)`
- [ ] Tauri command: `save_event_content(event_id: string, content: string)`
- [ ] Debounced auto-save
- [ ] Conflict detection (file changed externally)

### 6.4 Focus Mode `[frontend]`
- [ ] Collapse Left Pane
- [ ] Collapse Right Pane
- [ ] Keyboard shortcut to toggle
- [ ] Smooth transition animations

---

## Phase 7: User Flow - Time-Shifted Prep

### 7.1 Context Menu `[frontend]`
- [ ] Right-click on Event Block
- [ ] "Add Prep Task" option
- [ ] Date picker for "Do Date"
- [ ] Task title input

### 7.2 Linked Tasks `[backend]`
- [ ] Create task with `@before[Xd]:event-id` syntax in parent note/project
- [ ] Parse offset to calculate effective deadline from event time
- [ ] Resolve multiple event references (earliest = deadline)

### 7.3 Unified Task View `[both]`
- [ ] Query tasks by `do_date`
- [ ] Display in Today view with "Linked" badge
- [ ] Click to navigate to source event

---

## Phase 8: User Flow - Recurring Events

### 8.1 Recurrence Setup `[frontend]`
- [ ] Recurrence picker (Daily, Weekly, Monthly, Custom)
- [ ] End date / occurrence count
- [ ] Visual indicator for recurring events

### 8.2 Recurrence Backend `[backend]`
- [ ] Store recurrence rule in YAML (`recurrence: WEEKLY`)
- [ ] Generate virtual instances for calendar display
- [ ] Handle "edit this instance" vs "edit all"

### 8.3 History Context `[both]`
- [ ] Query previous instances by series ID
- [ ] Display "Last Week's Open Tasks" in Right Pane
- [ ] One-click import of unfinished tasks

---

## Phase 9: User Flow - Archive

### 9.1 Auto-Archive Logic `[backend]`
- [ ] Detect events with past dates
- [ ] Set status to `archived` (or move to `/archive/`)
- [ ] Exclude from active queries by default

### 9.2 Archive UI `[frontend]`
- [ ] Gray out past events on Calendar
- [ ] Read-only view for archived events
- [ ] Completed tasks summary

### 9.3 Search `[both]`
- [ ] Global search command (Cmd+K)
- [ ] Search events, notes, and tasks
- [ ] Include archived items option
- [ ] Fuzzy matching

---

## Phase 10: Unified Task View

### 10.1 Task Query Engine `[backend]`
- [ ] Query: Floating notes created today
- [ ] Query: Tasks from today's events (Agenda)
- [ ] Query: Tasks with `do_date == today` (Prep)
- [ ] Query: Overdue tasks

### 10.2 Today View UI `[frontend]`
- [ ] Section: Overdue (Red styling)
- [ ] Section: Events chronologically (with embedded tasks)
- [ ] Section: Floating/Anytime tasks
- [ ] Checkbox toggle updates file

---

## Phase 11: Polish & Micro-Interactions

### 11.1 Drag & Drop Polish `[frontend]`
- [ ] Smooth ghost following cursor
- [ ] 15-minute grid snapping
- [ ] Drop zone highlighting
- [ ] Animation on drop completion

### 11.2 Bi-directional Sync `[both]`
- [ ] Checkbox change → immediate file update
- [ ] File change → UI hot reload
- [ ] Optimistic UI updates with rollback on error

### 11.3 Keyboard Shortcuts `[frontend]`
- [ ] Navigate calendar (arrows)
- [ ] Quick capture (global hotkey)
- [ ] Focus mode toggle
- [ ] Search (Cmd+K)
- [ ] New event (Cmd+N)

### 11.4 Animations & Transitions `[frontend]`
- [ ] Pane collapse/expand
- [ ] View mode transitions
- [ ] Card hover lift effects
- [ ] Loading states

---

## Phase 12: Settings & Configuration

### 12.1 User Preferences `[both]`
- [ ] Default view (Day/Week/Month)
- [ ] First day of week
- [ ] Working hours range
- [ ] Theme (light/dark - future)

### 12.2 Data Location `[backend]`
- [ ] Configurable vault/data directory
- [ ] Migration between locations
- [ ] Backup/export functionality

---

## Non-Functional Requirements

### Performance `[both]`
- [ ] Index 1000+ files in < 1 second
- [ ] Calendar render < 100ms
- [ ] File save < 50ms

### Reliability `[backend]`
- [ ] Graceful handling of corrupted files
- [ ] Atomic file writes (temp file + rename)
- [ ] Crash recovery (unsaved changes)

### Testing
- [ ] Unit tests for parsers `[backend]`
- [ ] Unit tests for index queries `[backend]`
- [ ] Component tests `[frontend]`
- [ ] E2E tests for user flows `[both]`
