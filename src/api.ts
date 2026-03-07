/**
 * Type-safe wrappers for Gera Python backend commands.
 *
 * Each exported function calls the corresponding `@commands.command()`
 * python handler via pytauri's `pyInvoke`.
 */

import { pyInvoke } from "tauri-plugin-pytauri-api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DataRootStatus {
  path: string;
  structure: Record<string, boolean>;
}

export interface RenderMarkdownResponse {
  html: string;
  title: string;
  frontmatter: Record<string, unknown>;
  event_ids: string[];
  project_ids: string[];
}

export interface EventEntity {
  id: string;
  source: string;
  from_: string;
  to: string;
  name: string;
  description: string;
  participants: string[];
}

export interface NoteEntity {
  filename: string;
  title: string;
  body_preview: string;
  event_ids: string[];
  project_ids: string[];
  raw_content: string;
}

export interface ProjectEntity {
  id: string;
  filename: string;
  title: string;
  body_preview: string;
  event_ids: string[];
  raw_content: string;
}

export interface TimeReference {
  modifier: string;
  amount: number;
  unit: string;
  target_id: string;
}

export interface TaskEntity {
  text: string;
  completed: boolean;
  raw_line: string;
  source_file: string;
  line_number: number;
  deadline: string | null;
  event_ids: string[];
  project_ids: string[];
  time_references: TimeReference[];
  resolved_event_names: Record<string, string>;
  resolved_project_names: Record<string, string>;
}

export interface NoteContentResponse {
  filename: string;
  raw_content: string;
  html: string;
  title: string;
  event_ids: string[];
  project_ids: string[];
}

export interface PageRequest {
  limit?: number;
  cursor?: string | null;
}

export interface EventListRequest extends PageRequest {
  from_?: string;
  to?: string;
}

export interface NoteListRequest extends PageRequest {
  event_id?: string;
  project_id?: string;
}

export interface TaskListRequest extends PageRequest {
  deadline_from?: string;
  deadline_to?: string;
  event_id?: string;
  project_id?: string;
}

export interface EventListResponse {
  events: EventEntity[];
  next_cursor: string | null;
}

export interface NoteListResponse {
  notes: NoteEntity[];
  next_cursor: string | null;
}

export interface ProjectListResponse {
  projects: ProjectEntity[];
  next_cursor: string | null;
}

export interface TaskListResponse {
  tasks: TaskEntity[];
  next_cursor: string | null;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

/** Get the current data root directory and its structure health. */
export async function getDataRootStatus(): Promise<DataRootStatus> {
  return pyInvoke<DataRootStatus>("get_data_root_status", null);
}

/** Render a Gera markdown document (with optional YAML frontmatter) to HTML. */
export async function renderMarkdown(
  content: string
): Promise<RenderMarkdownResponse> {
  return pyInvoke<RenderMarkdownResponse>("render_markdown_cmd", { content });
}

/** List all events from events.yaml. */
export async function listEventsPage(
  request: EventListRequest = {}
): Promise<EventListResponse> {
  return pyInvoke<EventListResponse>("list_events", request);
}

/** Helper: Get ISO date strings for week boundaries. */
export function getWeekDateRange(fromDate: Date = new Date()): { from_: string; to: string } {
  const mon = new Date(fromDate);
  mon.setDate(fromDate.getDate() - ((fromDate.getDay() + 6) % 7));
  const sun = new Date(mon);
  sun.setDate(mon.getDate() + 6);
  sun.setHours(23, 59, 59, 999);
  return { from_: mon.toISOString(), to: sun.toISOString() };
}

/** List all events, internally paging through backend cursors. */
export async function listEvents(
  filters: Omit<EventListRequest, "cursor" | "limit"> = {}
): Promise<EventEntity[]> {
  const events: EventEntity[] = [];
  let cursor: string | null = null;
  do {
    const page = await listEventsPage({ ...filters, cursor, limit: 500 });
    events.push(...page.events);
    cursor = page.next_cursor;
  } while (cursor !== null);
  return events;
}

/** List notes from notes/ with cursor pagination and relationship filters. */
export async function listNotesPage(
  request: NoteListRequest = {}
): Promise<NoteListResponse> {
  return pyInvoke<NoteListResponse>("list_notes", request);
}

/** List all notes, internally paging through backend cursors. */
export async function listNotes(
  filters: Omit<NoteListRequest, "cursor" | "limit"> = {}
): Promise<NoteEntity[]> {
  const notes: NoteEntity[] = [];
  let cursor: string | null = null;
  do {
    const page = await listNotesPage({ ...filters, cursor, limit: 500 });
    notes.push(...page.notes);
    cursor = page.next_cursor;
  } while (cursor !== null);
  return notes;
}

/** List projects from projects/ with cursor pagination. */
export async function listProjectsPage(
  request: PageRequest = {}
): Promise<ProjectListResponse> {
  return pyInvoke<ProjectListResponse>("list_projects", request);
}

/** List all projects, internally paging through backend cursors. */
export async function listProjects(): Promise<ProjectEntity[]> {
  const projects: ProjectEntity[] = [];
  let cursor: string | null = null;
  do {
    const page = await listProjectsPage({ cursor, limit: 500 });
    projects.push(...page.projects);
    cursor = page.next_cursor;
  } while (cursor !== null);
  return projects;
}

/** List floating tasks from tasks.md with cursor pagination and filters. */
export async function listFloatingTasksPage(
  request: TaskListRequest = {}
): Promise<TaskListResponse> {
  return pyInvoke<TaskListResponse>("list_floating_tasks", request);
}

/** List all floating tasks, internally paging through backend cursors. */
export async function listFloatingTasks(
  filters: Omit<TaskListRequest, "cursor" | "limit"> = {}
): Promise<TaskEntity[]> {
  const tasks: TaskEntity[] = [];
  let cursor: string | null = null;
  do {
    const page = await listFloatingTasksPage({ ...filters, cursor, limit: 500 });
    tasks.push(...page.tasks);
    cursor = page.next_cursor;
  } while (cursor !== null);
  return tasks;
}

/** Read and render a specific note by filename. */
export async function getNoteContent(
  filename: string
): Promise<NoteContentResponse> {
  return pyInvoke<NoteContentResponse>("get_note_content", { filename });
}

/** Update a note file with new markdown content. */
export async function updateNoteContent(
  filename: string,
  content: string
): Promise<void> {
  return pyInvoke<void>("update_note_content", { filename, content });
}

// ============================================================================
// SEARCH COMMANDS - FTS5 Full-Text Search
// ============================================================================

/** Full-text search events using FTS5. */
export async function searchEvents(query: string): Promise<EventEntity[]> {
  const response = await pyInvoke<{ events: EventEntity[] }>("search_events", { query });
  return response.events;
}

/** Full-text search notes using FTS5. */
export async function searchNotes(query: string): Promise<NoteEntity[]> {
  const response = await pyInvoke<{ notes: NoteEntity[] }>("search_notes", { query });
  return response.notes;
}

/** Full-text search projects using FTS5. */
export async function searchProjects(query: string): Promise<ProjectEntity[]> {
  const response = await pyInvoke<{ projects: ProjectEntity[] }>("search_projects", { query });
  return response.projects;
}

/** Full-text search tasks using FTS5. */
export async function searchTasks(query: string): Promise<TaskEntity[]> {
  const response = await pyInvoke<{ tasks: TaskEntity[] }>("search_tasks", { query });
  return response.tasks;
}

// ============================================================================
// TASK MUTATION COMMANDS
// ============================================================================

/** Toggle a task's completion status in its source markdown file. */
export async function toggleTask(
  sourceFile: string,
  lineNumber: number
): Promise<void> {
  return pyInvoke<void>("toggle_task", {
    source_file: sourceFile,
    line_number: lineNumber,
  });
}

/** Create a new floating task in tasks.md. */
export async function createTask(text: string): Promise<TaskEntity> {
  const response = await pyInvoke<{ task: TaskEntity }>("create_task", { text });
  return response.task;
}

/** Delete a task line from its source file. */
export async function deleteTask(
  sourceFile: string,
  lineNumber: number
): Promise<void> {
  return pyInvoke<void>("delete_task", {
    source_file: sourceFile,
    line_number: lineNumber,
  });
}

/** Update the text of an existing task line. */
export async function updateTask(
  sourceFile: string,
  lineNumber: number,
  newText: string
): Promise<void> {
  return pyInvoke<void>("update_task", {
    source_file: sourceFile,
    line_number: lineNumber,
    new_text: newText,
  });
}

/** Create a new note file. */
export async function createNote(
  filename: string,
  content: string = "",
  eventIds?: string[],
  projectIds?: string[]
): Promise<NoteEntity> {
  const response = await pyInvoke<{ note: NoteEntity }>("create_note", {
    filename,
    content,
    event_ids: eventIds ?? null,
    project_ids: projectIds ?? null,
  });
  return response.note;
}

/** Delete a note file. */
export async function deleteNote(filename: string): Promise<void> {
  return pyInvoke<void>("delete_note", { filename });
}
