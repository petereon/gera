import { EventEntity, TaskEntity } from '../../types';
import { EventTaskGroup, TaskGroup } from './TaskGroup';
import { EmptyState } from '../shared/EmptyState';

interface TaskListProps {
  filteredEventsWithTasks: EventEntity[];
  filteredStandaloneTasks: TaskEntity[];
  getTasksForEvent: (eventId: string) => TaskEntity[];
}

export function TaskList({ 
  filteredEventsWithTasks, 
  filteredStandaloneTasks, 
  getTasksForEvent 
}: TaskListProps) {
  const isEmpty = filteredEventsWithTasks.length === 0 && filteredStandaloneTasks.length === 0;

  if (isEmpty) {
    return <EmptyState message="No tasks yet" />;
  }

  return (
    <div className="tasks-list">
      {/* Events with tasks */}
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

      {/* Standalone tasks */}
      {filteredStandaloneTasks.length > 0 && (
        <TaskGroup 
          title="Standalone Tasks" 
          tasks={filteredStandaloneTasks} 
        />
      )}
    </div>
  );
}
