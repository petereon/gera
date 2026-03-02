# **Project Specification: Gera**

## **1. Product Vision**

**Core Premise:** "The Meeting *is* the Folder."
**Problem:** Productivity tools (Notes/Tasks) are disconnected from Time (Calendar).
**Solution:** A desktop app where generic notes/tasks ("Floating") are dragged onto a timeline to become actionable ("Anchored"). The Event acts as a container for work, not just a time slot.

---

## **2. Technical Architecture**

### **2.1. Persistence Layer (Local-First)**

* **Storage Strategy:** File-system based. No proprietary database.
* **Format:** YAML for events, Markdown (`.md`) with YAML Frontmatter for notes/projects.
* **File Structure:**
* `events.yaml` - YAML file with calendar event definitions.
* `tasks.md` - Floating tasks (not associated with anything)
* `/notes/` - Markdown files (Floating/Inbox). Tasks inside inherit note-level associations.
* `/projects/` - Markdown files for grouping work. ID = filename.



### **2.2. State Management (The Indexer)**

* **Constraint:** Direct file reading is too slow for rendering a calendar grid.
* **Solution:** On app startup, an **In-Memory Index** (e.g., SQLite, PouchDB, or a custom JSON Tree) parses all YAML headers.
* **Sync:** Watcher processes monitor file changes.
* *App -> File:* UI changes write immediately to disk.
* *File -> App:* External edits (e.g., VS Code) trigger a hot-reload of the Index.



---

## **3. Data Model & Schema**

*See `specs/data-model-spec.md` for the canonical reference. Summary below.*

**Inheritance rule:** When tasks inherit associations from their parent note/project, values are **merged** (not overridden) with anything already defined on the task.

### **Event Entity (`/events/<id>.yaml`)**

```yaml
events:
  - id: some-id
    source: google-calendar    # or local, outlook, apple
    from: 2026-05-20T14:00
    to: 2026-05-20T15:30
    name: "Quarterly Review"
    description: "..."
    participants: ["email@example.com"]
```

### **Note Entity (`/notes/<name>.md`)**

```yaml
---
event_ids:
  - event-1
  - event-2
project_ids:
  - project-1
---
# Title (H1 used as display title, fallback: first few words)

Markdown body with embedded tasks.
- [ ] Task inherits note's event_ids and project_ids
```

### **Project Entity (`/projects/<name>.md`)**

```yaml
---
event_ids:
  - event-1
---
# Project Name

Markdown body. ID = filename. Cannot have a deadline (use events for that).
- [ ] Task inherits the project automatically
```

### **Task Entity (Virtual)**

* Tasks are **line-items** (`- [ ]` / `- [x]`) inside Markdown files (notes or projects).
* **Event linking:** `- [ ] Draft Slides @event-id`
* **Prep tasks (with offset):** `- [ ] Prepare @before[2d]:event-id`
* **Time deadline:** `- [ ] Buy flowers @2026-03-03T18:00`
* **Project tagging:** `- [ ] Fix handles #project-id`
* **Multiple events:** Earliest event time is used as deadline.
* **Supported time units:** Y, M, W, D, h, m (case-sensitive).

---

## **4. UI Design System: "Floating Islands"**

**Visual Metaphor:** Distinct, rounded panels floating above a soft gray background. Depth is conveyed via layered shadows, not borders.

### **4.1. Layout Grid (CSS Grid)**

* **Background:** `var(--app-bg)` (Soft Gray #F5F7FA).
* **Columns:** 3-Pane Fixed/Flex Layout with `32px` gaps.
1. **Left Pane (Staging):** Fixed ~260px. Navigation & Inbox.
2. **Center Pane (Active):** Flex `1fr`. Calendar Grid or Document Editor.
3. **Right Pane (Inspector):** Fixed ~320px. Context & Metadata.



### **4.2. Component Styling**

* **Islands:** `bg-white`, `rounded-3xl` (24px), `shadow-md`.
* **Elements:** `rounded-full` (Pills) for buttons/inputs.
* **Typography:** Sans-serif (Inter/Geist), dark gray text, high whitespace.
* **Accent:** Soft Blue (`#3B82F6`) for active states/events.

---

## **5. Core User Flows**

### **Flow 1: Quick Capture (The Inbox)**

* **Trigger:** Global Hotkey or Input Field in Left Pane.
* **Action:** User types a raw string.
* **System:** Creates a new `.md` file in `/notes/inbox/`.
* **UI:** Appears instantly in the **Left Pane** list as a draggable card.

### **Flow 2: Anchoring (The Magic Moment)**

* **Trigger:** User drags a Note Card from **Left Pane** → **Center Pane (Calendar)**.
* **Interaction:**
* *Hover:* A translucent "Ghost Event" snaps to the grid (15min slots).
* *Drop:* The Note Card is removed from the Left Pane.


* **System:**
1. Creates a new event entry in `/events/` with `from`/`to` based on dropped time slot.
2. Links the note to the event by adding the event ID to the note's `event_ids` frontmatter.


* **UI:** The Calendar Grid now shows a solid Event Block containing the note title.

### **Flow 3: Deep Work (The Workspace)**

* **Trigger:** Click an Event Block.
* **UI Transition:** Center Pane transforms from **Calendar Grid** → **Document Editor**.
* **Features:**
* Full Markdown editing.
* Embedded Checklist rendering.
* "Focus Mode" (Right/Left panes can be collapsed).



### **Flow 4: Time-Shifted Prep (The "Do Date")**

* **Context:** Event is on Friday. User wants to work on it Tuesday.
* **Action:** User right-clicks Friday Event → "Add Prep Task".
* **System:**
1. Creates a task linked to the Event ID using `@before[Xd]:event-id` syntax.
2. The offset determines how many days/hours before the event the task should appear.


* **UI:** The task appears in the **Unified Task View** for Tuesday, with a "Linked" badge pointing to Friday's event.

### **Flow 5: Recurring Context (The History)**

* **Context:** "Weekly Team Sync" (Series).
* **Action:** User opens *Today's* instance.
* **System:** Queries the Index for previous events with `same_series_id` or `same_title`.
* **UI:**
* **Right Pane** displays "Last Week's Open Tasks."
* Allows 1-click import of unfinished items to current note.



### **Flow 6: The Archive (Post-Event)**

* **Context:** Event date has passed.
* **System:** Event remains in `/events/` but status changes to `archived` in UI.
* **UI:**
* Event grays out on Calendar.
* Searchable via "Global Search."
* Read-only summary view showing completed tasks and final notes.



---

## **6. Key Logic: The "Unified Task View"**

*This is the logic for the "Today" view in the Left/Right panes.*

**Query Logic (Pseudo-SQL):**
Display tasks where:

1. Source is **Floating Note** AND Created_Date == Today.
2. Source is **Event** AND Event_Date == Today (Agenda).
3. Source is **Task** (inside future event) AND Do_Date == Today (Prep).

**Visual Sorting:**

1. **Overdue** (Red)
2. **Events** (Chronological 9AM - 5PM) - *Tasks embedded in these events show here.*
3. **Floating/Anytime** (Bottom list).

---

## **7. Interaction Details (Micro-Interactions)**

* **Ghosting:** Dragging must show a semi-transparent preview of the result.
* **Snapping:** Calendar drops snap to 15-minute grid lines.
* **Bi-directional Editing:** Checking a box in the "Unified View" must update the text string `[ ]` to `[x]` in the underlying Markdown file immediately.