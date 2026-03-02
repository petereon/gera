import { EventEntity, TaskEntity } from '../../types';
import { TaskItem } from './TaskItem';
import { formatEventDate, formatEventTime } from '../../utils/dateFormatting';

interface TaskGroupProps {
  title: string;
  subtitle?: string;
  tasks: TaskEntity[];
}

export function TaskGroup({ title, subtitle, tasks }: TaskGroupProps) {
  return (
    <div className="task-group">
      <div className="task-category">
        {title}
        {subtitle && (
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginLeft: '8px' }}>
            {subtitle}
          </span>
        )}
      </div>
      {tasks.map((task, i) => (
        <TaskItem key={i} task={task} />
      ))}
    </div>
  );
}

interface EventTaskGroupProps {
  event: EventEntity;
  tasks: TaskEntity[];
}

export function EventTaskGroup({ event, tasks }: EventTaskGroupProps) {
  const subtitle = `${formatEventDate(event.from_)} ${formatEventTime(event.from_)}`;
  
  return <TaskGroup title={event.name} subtitle={subtitle} tasks={tasks} />;
}
