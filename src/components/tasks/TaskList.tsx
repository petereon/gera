import { useState } from 'react';
import { EventEntity, TaskEntity } from '../../types';
import { EventTaskGroup, TaskGroup } from './TaskGroup';
import { EmptyState } from '../shared/EmptyState';
import { TaskItem } from './TaskItem';
import { SearchInput } from '../shared/SearchInput';

export type TasksViewMode = 'grouped' | 'timeline';

interface TaskListProps {
  filteredEventsWithTasks: EventEntity[];
  filteredOtherTasks: TaskEntity[];
  timelineScheduledTasks: TaskEntity[];
  timelineUnscheduledTasks: TaskEntity[];
  getTasksForEvent: (eventId: string) => TaskEntity[];
  viewMode: TasksViewMode;
}

/** Separately scrollable + searchable block for unscheduled tasks at the bottom of Timeline. */
function UnscheduledTasksBlock({ tasks }: { tasks: TaskEntity[] }) {
  const [search, setSearch] = useState('');
  const filtered = tasks.filter(
    (t) => !search || t.text.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="unscheduled-block">
      <div className="unscheduled-block-header">
        <span className="task-category" style={{ margin: 0 }}>Unscheduled</span>
        <span className="unscheduled-block-count">{tasks.length}</span>
      </div>
      <div className="unscheduled-block-search">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search unscheduled…"
          className="unscheduled-search-input"
        />
      </div>
      <div className="unscheduled-block-scroll">
        {filtered.length === 0 ? (
          <p className="unscheduled-block-empty">No matching tasks</p>
        ) : (
          filtered.map((task, i) => (
            <TaskItem key={`${task.source_file}:${task.line_number}:${i}`} task={task} />
          ))
        )}
      </div>
    </div>
  );
}

export function TaskList({
  filteredEventsWithTasks,
  filteredOtherTasks,
  timelineScheduledTasks,
  timelineUnscheduledTasks,
  getTasksForEvent,
  viewMode,
}: TaskListProps) {
  if (viewMode === 'timeline') {
    const hasScheduled = timelineScheduledTasks.length > 0;
    const hasUnscheduled = timelineUnscheduledTasks.length > 0;

    if (!hasScheduled && !hasUnscheduled) return <EmptyState message="No tasks yet" />;

    return (
      <div className="tasks-list tasks-list--timeline">
        <div className="timeline-scheduled-pane">
          {hasScheduled ? (
            timelineScheduledTasks.map((task, i) => (
              <TaskItem key={`${task.source_file}:${task.line_number}:${i}`} task={task} />
            ))
          ) : (
            <p className="timeline-scheduled-empty">No scheduled tasks</p>
          )}
        </div>
        {hasUnscheduled && (
          <UnscheduledTasksBlock tasks={timelineUnscheduledTasks} />
        )}
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

