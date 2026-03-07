import { useRef, useState } from 'react';
import { useAppStore } from '../../stores/useAppStore';
import { useTaskFiltering } from '../../hooks/useTaskFiltering';
import { createTask } from '../../api';
import { SearchInput } from '../shared/SearchInput';
import { TaskList, TasksViewMode } from './TaskList';
import { PlusIcon } from '../icons/Icons';

interface TasksViewProps {}

export function TasksView({}: TasksViewProps) {
  const events = useAppStore((state) => state.events);
  const tasks = useAppStore((state) => state.tasks);
  const tasksSearch = useAppStore((state) => state.tasksSearch);
  const setTasksSearch = useAppStore((state) => state.setTasksSearch);

  const [showModal, setShowModal] = useState(false);
  const [newTaskText, setNewTaskText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState<TasksViewMode>('grouped');
  const backdropRef = useRef<HTMLDivElement>(null);

  const { filteredEventsWithTasks, filteredOtherTasks, timelineTasks, getTasksForEvent } =
    useTaskFiltering(tasks, events, tasksSearch);

  const closeModal = () => {
    setNewTaskText('');
    setShowModal(false);
  };

  const handleCreateTask = async () => {
    const text = newTaskText.trim();
    if (!text || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await createTask(text);
      closeModal();
    } catch (error) {
      console.error('Failed to create task:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleCreateTask();
    } else if (e.key === 'Escape') {
      closeModal();
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) closeModal();
  };

  return (
    <div className="tasks-view">
      <div className="tasks-header">
        <div className="section-header-row">
          <div className="section-label">TASKS</div>
          <div className="tasks-view-toggle">
            <button
              className={`tasks-view-toggle-btn${viewMode === 'grouped' ? ' active' : ''}`}
              onClick={() => setViewMode('grouped')}
            >
              By Event
            </button>
            <button
              className={`tasks-view-toggle-btn${viewMode === 'timeline' ? ' active' : ''}`}
              onClick={() => setViewMode('timeline')}
            >
              Timeline
            </button>
          </div>
          <button
            className="icon-btn"
            onClick={() => setShowModal(true)}
            aria-label="New task"
            title="New task"
          >
            <PlusIcon />
          </button>
        </div>
        <SearchInput
          value={tasksSearch}
          onChange={setTasksSearch}
          placeholder="Search by event, project, time-range..."
          className="tasks-search"
        />
      </div>
      <TaskList
        filteredEventsWithTasks={filteredEventsWithTasks}
        filteredOtherTasks={filteredOtherTasks}
        timelineTasks={timelineTasks}
        getTasksForEvent={getTasksForEvent}
        viewMode={viewMode}
      />

      {showModal && (
        <div className="modal-backdrop" ref={backdropRef} onClick={handleBackdropClick}>
          <div className="modal-panel">
            <h3 className="modal-title">New Task</h3>
            <input
              type="text"
              className="modal-input"
              placeholder="Task description…"
              value={newTaskText}
              onChange={(e) => setNewTaskText(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              disabled={isSubmitting}
            />
            <div className="modal-actions">
              <button className="modal-btn modal-btn--cancel" onClick={closeModal}>
                Cancel
              </button>
              <button
                className="modal-btn modal-btn--submit"
                onClick={handleCreateTask}
                disabled={!newTaskText.trim() || isSubmitting}
              >
                {isSubmitting ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
