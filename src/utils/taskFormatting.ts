import { TaskEntity } from '../api';

/**
 * Remove task references and formatting to display clean task text
 */
export function cleanTaskDisplay(task: TaskEntity): string {
  let display = task.text;
  
  // Remove time references: @modifier[amount unit]:target_id
  if (task.time_references) {
    for (const ref of task.time_references) {
      display = display.replace(
        `@${ref.modifier}[${ref.amount}${ref.unit}]:${ref.target_id}`,
        ""
      );
    }
  }
  
  // Remove event references
  if (task.event_ids && task.resolved_event_names) {
    for (const eid of task.event_ids) {
      const evName = task.resolved_event_names[eid];
      if (evName) {
        display = display.replace(`@${eid}`, "");
      }
    }
  }
  
  // Remove project references
  if (task.project_ids && task.resolved_project_names) {
    for (const pid of task.project_ids) {
      const projName = task.resolved_project_names[pid];
      if (projName) {
        display = display.replace(`#${pid}`, "");
      }
    }
  }
  
  // Remove ISO datetime references: @YYYY-MM-DDTHH:MM...
  display = display.replace(/@\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}/, "");
  
  return display.trim();
}

export interface TaskTags {
  eventTags: Array<{ id: string; name: string }>;
  projectTags: Array<{ id: string; name: string }>;
  hasDeadline: boolean;
}

/**
 * Extract event and project tags from a task for display
 */
export function getTaskTags(task: TaskEntity): TaskTags {
  const eventTags = Object.entries(task.resolved_event_names ?? {}).map(
    ([id, name]) => ({ id, name })
  );
  const projectTags = Object.entries(task.resolved_project_names ?? {}).map(
    ([id, name]) => ({ id, name })
  );
  const hasDeadline = !!task.deadline;
  
  return { eventTags, projectTags, hasDeadline };
}
