import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { TaskEntity } from '../../types';
import { Checkbox } from '../shared/Checkbox';
import { ClockIcon, LinkIcon, TrashIcon } from '../icons/Icons';
import { cleanTaskDisplay, getTaskTags } from '../../utils/taskFormatting';
import { formatEventDate, formatEventTime } from '../../utils/dateFormatting';
import { toggleTask, updateTask, deleteTask } from '../../api';
import { ConfirmDialog } from '../shared/ConfirmDialog';
import { useAppStore } from '../../stores/useAppStore';

interface TaskItemProps {
  task: TaskEntity;
}

export function TaskItem({ task }: TaskItemProps) {
  const display = cleanTaskDisplay(task);
  const { eventTags, projectTags, hasDeadline } = getTaskTags(task);
  const allEvents = useAppStore((state) => state.events);
  const notes = useAppStore((state) => state.notes);
  const allTasks = useAppStore((state) => state.tasks);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  const setFocusLine = useAppStore((state) => state.setFocusLine);
  const navigate = useNavigate();

  // Which event IDs appear literally as @id tokens in the task text (vs. inherited from note frontmatter)
  const ownEventIdsInText = (task.event_ids ?? []).filter((eid) =>
    new RegExp(`@${eid}(?=[^a-z0-9-]|$)`).test(task.text)
  );
  // Event IDs inherited from the note's frontmatter (can't be removed from here)
  const inheritedEventIds = (task.event_ids ?? []).filter((eid) => !ownEventIdsInText.includes(eid));
  const isStandalone = task.source_file === 'tasks.md';

  // Source label: note title, or "Standalone" for tasks.md tasks
  const sourceLabel = useMemo(() => {
    if (task.source_file === 'tasks.md') return 'Standalone';
    if (task.source_file.startsWith('notes/')) {
      const filename = task.source_file.replace(/^notes\//, '');
      const note = notes.find((n) => n.filename === filename);
      return note?.title || filename.replace(/\.md$/, '');
    }
    return task.source_file.replace(/^(projects|notes)\//, '').replace(/\.md$/, '');
  }, [task.source_file, notes]);

  const hasTags = eventTags.length > 0 || projectTags.length > 0 || hasDeadline;

  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [editEventIds, setEditEventIds] = useState<string[]>([]);
  const [showEventPicker, setShowEventPicker] = useState(false);
  const [eventSearch, setEventSearch] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const backdropRef = useRef<HTMLDivElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker when clicking outside
  useEffect(() => {
    if (!showEventPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowEventPicker(false);
        setEventSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showEventPicker]);

  const handleToggle = async () => {
    try {
      await toggleTask(task.source_file, task.line_number);
    } catch (error) {
      console.error('Failed to toggle task:', error);
    }
  };

  const openEdit = () => {
    setEditText(display);
    // For both standalone and note tasks, start with whatever @tokens are already in the task line
    setEditEventIds([...ownEventIdsInText]);
    setEditing(true);
  };

  const closeEdit = () => {
    setEditing(false);
    setEditText('');
    setEditEventIds([]);
    setShowEventPicker(false);
    setEventSearch('');
  };

  const handleSave = async () => {
    const baseText = editText.trim();
    if (!baseText || isSubmitting) return;
    setIsSubmitting(true);
    try {
      // For both standalone and note tasks: append @event-id tokens to the task line.
      // Inherited (frontmatter) events are not touched — they live in the note's YAML, not the task line.
      const fullText = editEventIds.length > 0
        ? `${baseText} ${editEventIds.map((id) => `@${id}`).join(' ')}`
        : baseText;
      await updateTask(task.source_file, task.line_number, fullText);
      closeEdit();
    } catch (err) {
      console.error('Failed to update task:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); handleSave(); }
    else if (e.key === 'Escape') closeEdit();
  };

  const handleDelete = async () => {
    try {
      await deleteTask(task.source_file, task.line_number);
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
    setConfirmDelete(false);
    closeEdit();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) closeEdit();
  };

  const handleGoToSource = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (task.source_file.startsWith('notes/')) {
      const noteFilename = task.source_file.replace(/^notes\//, '');
      const note = notes.find((n) => n.filename === noteFilename);
      if (note) {
        const noteTasks = allTasks
          .filter((t) => t.source_file === task.source_file)
          .sort((a, b) => a.line_number - b.line_number);
        const taskIdx = noteTasks.findIndex((t) => t.line_number === task.line_number);
        setFocusLine(taskIdx >= 0 ? taskIdx : 0);
        setSelectedNote(note);
        navigate('/notes');
      }
    }
  };

  return (
    <>
      <div className="task-item" onClick={openEdit}>
        <div onClick={(e) => e.stopPropagation()}>
          <Checkbox checked={task.completed} onChange={handleToggle} />
        </div>
        <div className="task-content">
          <span className={`task-text${task.completed ? ' completed' : ''}`}>
            {display}
          </span>
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
        {sourceLabel && !isStandalone && (
          <button
            className="task-source-label"
            onClick={handleGoToSource}
            title={`Go to ${task.source_file}`}
          >
            <LinkIcon />
            {sourceLabel}
          </button>
        )}
        {sourceLabel && isStandalone && (
          <span className="task-source-label task-source-label--static">{sourceLabel}</span>
        )}
      </div>

      {editing && createPortal(
        <div className="modal-backdrop" ref={backdropRef} onClick={handleBackdropClick}>
          <div className="modal-panel">
            <div className="modal-header">
              <h3 className="modal-title">Edit Task</h3>
              <button
                className="modal-delete-btn"
                onClick={() => setConfirmDelete(true)}
                title="Delete task"
              >
                <TrashIcon />
              </button>
            </div>
            <input
              type="text"
              className="modal-input"
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              disabled={isSubmitting}
            />

            {/* Event associations */}
            <div className="task-modal-events">
              <span className="task-modal-events-label">Events</span>
              <div className="task-modal-chips">
                {/* Inherited from note frontmatter — always read-only */}
                {inheritedEventIds.map((eid) => {
                  const name = task.resolved_event_names?.[eid] ?? allEvents.find((e) => e.id === eid)?.name ?? eid;
                  return (
                    <span key={eid} className="metadata-chip metadata-chip--event metadata-chip--readonly" title="Inherited from note">
                      @{name}
                    </span>
                  );
                })}

                {/* Editable inline tokens (both standalone and note tasks) */}
                {editEventIds.map((eid) => {
                  const name = task.resolved_event_names?.[eid]
                    ?? allEvents.find((e) => e.id === eid)?.name
                    ?? eid;
                  return (
                    <span key={eid} className="metadata-chip metadata-chip--event">
                      @{name}
                      <button
                        className="metadata-chip-remove"
                        onClick={() => setEditEventIds((ids) => ids.filter((id) => id !== eid))}
                        title="Remove event"
                      >×</button>
                    </span>
                  );
                })}

                {/* Add event picker */}
                <div className="metadata-add-wrapper" ref={pickerRef}>
                  <button
                    className="metadata-chip metadata-chip--add"
                    onClick={() => { setShowEventPicker((v) => !v); setEventSearch(''); }}
                  >
                    + Event
                  </button>
                  {showEventPicker && (
                    <div className="metadata-event-picker">
                      <input
                        className="metadata-picker-search"
                        placeholder="Search events…"
                        value={eventSearch}
                        onChange={(e) => setEventSearch(e.target.value)}
                        autoFocus
                      />
                      <div className="metadata-picker-list">
                        {allEvents
                          .filter((e) =>
                            !editEventIds.includes(e.id) &&
                            !inheritedEventIds.includes(e.id) &&
                            e.name.toLowerCase().includes(eventSearch.toLowerCase())
                          )
                          .slice(0, 10)
                          .map((e) => (
                            <button
                              key={e.id}
                              className="metadata-picker-item"
                              onClick={() => {
                                setEditEventIds((ids) => [...ids, e.id]);
                                setShowEventPicker(false);
                                setEventSearch('');
                              }}
                            >
                              {e.name}
                            </button>
                          ))}
                        {allEvents.filter((e) =>
                          !editEventIds.includes(e.id) &&
                          !inheritedEventIds.includes(e.id) &&
                          e.name.toLowerCase().includes(eventSearch.toLowerCase())
                        ).length === 0 && (
                          <span className="metadata-picker-empty">No events found</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {inheritedEventIds.length === 0 && editEventIds.length === 0 && !showEventPicker && (
                  <span className="task-modal-events-empty">None</span>
                )}
              </div>
            </div>

            <div className="modal-actions">
              <button className="modal-btn modal-btn--cancel" onClick={closeEdit}>
                Cancel
              </button>
              <button
                className="modal-btn modal-btn--submit"
                onClick={handleSave}
                disabled={!editText.trim() || isSubmitting}
              >
                {isSubmitting ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Delete task"
          message={`"${display}" will be permanently deleted.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </>
  );
}
