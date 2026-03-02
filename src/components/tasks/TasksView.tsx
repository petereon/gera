import { useAppStore } from '../../stores/useAppStore';
import { useTaskFiltering } from '../../hooks/useTaskFiltering';
import { SearchInput } from '../shared/SearchInput';
import { TaskList } from './TaskList';

interface TasksViewProps {}

export function TasksView({}: TasksViewProps) {
  const events = useAppStore((state) => state.events);
  const tasks = useAppStore((state) => state.tasks);
  const tasksSearch = useAppStore((state) => state.tasksSearch);
  const setTasksSearch = useAppStore((state) => state.setTasksSearch);

  const { filteredEventsWithTasks, filteredStandaloneTasks, getTasksForEvent } =
    useTaskFiltering(tasks, events, tasksSearch);

  return (
    <div className="tasks-view">
      <div className="tasks-header">
        <div className="section-label">TASKS</div>
        <SearchInput
          value={tasksSearch}
          onChange={setTasksSearch}
          placeholder="Search by event, project, time-range..."
          className="tasks-search"
        />
      </div>
      <TaskList
        filteredEventsWithTasks={filteredEventsWithTasks}
        filteredStandaloneTasks={filteredStandaloneTasks}
        getTasksForEvent={getTasksForEvent}
      />
    </div>
  );
}
