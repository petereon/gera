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

export interface TaskEntity {
  text: string;
  completed: boolean;
  raw_line: string;
  source_file: string;
  line_number: number;
}

export interface NoteContentResponse {
  filename: string;
  raw_content: string;
  html: string;
  title: string;
  event_ids: string[];
  project_ids: string[];
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
export async function listEvents(): Promise<EventEntity[]> {
  const res = await pyInvoke<{ events: EventEntity[] }>("list_events", null);
  return res.events;
}

/** List all notes from notes/. */
export async function listNotes(): Promise<NoteEntity[]> {
  const res = await pyInvoke<{ notes: NoteEntity[] }>("list_notes", null);
  return res.notes;
}

/** List all projects from projects/. */
export async function listProjects(): Promise<ProjectEntity[]> {
  const res = await pyInvoke<{ projects: ProjectEntity[] }>("list_projects", null);
  return res.projects;
}

/** List all floating tasks from tasks.md. */
export async function listFloatingTasks(): Promise<TaskEntity[]> {
  const res = await pyInvoke<{ tasks: TaskEntity[] }>("list_floating_tasks", null);
  return res.tasks;
}

/** Read and render a specific note by filename. */
export async function getNoteContent(
  filename: string
): Promise<NoteContentResponse> {
  return pyInvoke<NoteContentResponse>("get_note_content", { filename });
}
