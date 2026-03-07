import { EventEntity, TaskEntity } from '../../types';
import { EventTaskGroup, TaskGroup } from './TaskGroup';
import { EmptyState } from '../shared/EmptyState';
import { TaskItem } from './TaskItem';

export type TasksViewMode = 'grouped' | 'timeline';

interface TaskListProps {
  filteredEventsWithTasks: EventEntity[];
  filteredOtherTasks: TaskEntity[];
  timelineTasks: TaskEntity[];
  getTasksForEvent: (eventId: string) => TaskEntity[];
  viewMode: TasksViewMode;
}

export function TaskList({
  filteredEventsWithTasks,
  filteredOtherTasks,
  timelineTasks,
  getTasksForEvent,
  viewMode,
}: TaskListProps) {
  if (viewMode === 'timeline') {
    if (timelineTasks.length === 0) return <EmptyState message="No tasks yet" />;
    return (
      <div className="tasks-list tasks-list--timeline">
        {timelineTasks.map((task, i) => (
          <TaskItem key={`${task.source_file}:${task.line_number}:${i}`} task={task} />
        ))}
      </div>
    );
  }

  // Grouped view
  const isEmpty = filteredEventsWithTasks.length === 0 && filteredOtherTasks.length === 0;
  if (isEmpty) return <EmptyState message="No tasks yet" />;

  return (
    <div className="tasks-list">
      {filteredEventsWithTasks.map((event) => {
        const eventTasks = getTasksForEvent(event.id);
        if (eventTasks.length === 0) return null;
        return (
          <EventTaskGroup
            key={event.id}
            event={event}
            tasks={eventTasks}
          />
        );
      })}
      {filteredOtherTasks.length > 0 && (
        <TaskGroup
          title="Other Tasks"
          tasks={filteredOtherTasks}
        />
      )}
    </div>
  );
}
