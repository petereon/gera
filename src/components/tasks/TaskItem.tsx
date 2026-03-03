import { TaskEntity } from '../../types';
import { Checkbox } from '../shared/Checkbox';
import { ClockIcon } from '../icons/Icons';
import { cleanTaskDisplay, getTaskTags } from '../../utils/taskFormatting';
import { formatEventDate, formatEventTime } from '../../utils/dateFormatting';
import { toggleTask } from '../../api';

interface TaskItemProps {
  task: TaskEntity;
}

export function TaskItem({ task }: TaskItemProps) {
  const display = cleanTaskDisplay(task);
  const { eventTags, projectTags, hasDeadline } = getTaskTags(task);
  const hasTags = eventTags.length > 0 || projectTags.length > 0 || hasDeadline;

  const handleToggle = async () => {
    try {
      await toggleTask(task.source_file, task.line_number);
      // The backend will emit gera://data-changed, which will trigger a re-fetch
    } catch (error) {
      console.error('Failed to toggle task:', error);
    }
  };

  return (
    <div className="task-item">
      <Checkbox checked={task.completed} onChange={handleToggle} />
      <div className="task-content">
        <span className={task.completed ? "completed" : ""}>{display}</span>
        {hasTags && (
          <div className="task-tags">
            {eventTags.map((tag) => (
              <span key={tag.id} className="task-tag task-tag--event">
                @{tag.name}
              </span>
            ))}
            {projectTags.map((tag) => (
              <span key={tag.id} className="task-tag task-tag--project">
                #{tag.name}
              </span>
            ))}
            {hasDeadline && (
              <span className="task-tag task-tag--deadline">
                <ClockIcon />
                {formatEventDate(task.deadline!)} {formatEventTime(task.deadline!)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
