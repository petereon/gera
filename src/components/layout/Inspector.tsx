import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../stores/useAppStore';
import {
  ClockIcon,
  UsersIcon,
  DocumentIcon,
  PencilIcon,
  CloseIcon,
} from '../icons/Icons';
import { Checkbox } from '../shared/Checkbox';
import { NoteTile } from '../notes/NoteTile';
import { cleanTaskDisplay } from '../../utils/taskFormatting';
import { formatEventDate, formatEventTime } from '../../utils/dateFormatting';
import { toggleTask } from '../../api';
import { EventEditModal } from '../calendar/EventEditModal';

interface InspectorProps {
  isVisible: boolean;
  /** When true the panel renders as a portal overlay instead of a grid column. */
  isModal?: boolean;
}

export function Inspector({ isVisible, isModal = false }: InspectorProps) {
  const navigate = useNavigate();
  const selectedEvent = useAppStore((state) => state.selectedEvent);
  const setSelectedEvent = useAppStore((state) => state.setSelectedEvent);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  const setReturnView = useAppStore((state) => state.setReturnView);
  const notes = useAppStore((state) => state.notes);
  const tasks = useAppStore((state) => state.tasks);
  const [editingEvent, setEditingEvent] = useState(false);

  const linkedNotes = selectedEvent
    ? notes.filter((n) => n.event_ids.includes(selectedEvent.id))
    : [];

  const linkedTasks = selectedEvent
    ? tasks.filter((t) => t.event_ids.includes(selectedEvent.id))
    : [];

  if (!isVisible) return null;

  // In modal mode: only show when an event is selected; render via portal
  if (isModal) {
    if (!selectedEvent) return null;

    return createPortal(
      <div className="inspector-modal-backdrop" onClick={() => setSelectedEvent(null)}>
        <div className="inspector-modal-sheet" onClick={(e) => e.stopPropagation()}>
          <InspectorContent
            selectedEvent={selectedEvent}
            linkedNotes={linkedNotes}
            linkedTasks={linkedTasks}
            notes={notes}
            editingEvent={editingEvent}
            setEditingEvent={setEditingEvent}
            navigate={navigate}
            setSelectedNote={setSelectedNote}
            setReturnView={setReturnView}
            closeButton={
              <button className="inspector-modal-close" onClick={() => setSelectedEvent(null)}>
                <CloseIcon />
              </button>
            }
          />
        </div>
      </div>,
      document.body
    );
  }

  // Normal sidebar-column mode
  return (
    <>
      <div className="right-column">
        <InspectorContent
          selectedEvent={selectedEvent}
          linkedNotes={linkedNotes}
          linkedTasks={linkedTasks}
          notes={notes}
          editingEvent={editingEvent}
          setEditingEvent={setEditingEvent}
          navigate={navigate}
          setSelectedNote={setSelectedNote}
          setReturnView={setReturnView}
        />
      </div>

      {editingEvent && selectedEvent && (
        <EventEditModal event={selectedEvent} onClose={() => setEditingEvent(false)} />
      )}
    </>
  );
}

/** Shared content extracted so both modes can render it identically. */
function InspectorContent({
  selectedEvent,
  linkedNotes,
  linkedTasks,
  notes: _notes,
  editingEvent,
  setEditingEvent,
  navigate,
  setSelectedNote,
  setReturnView,
  closeButton: _closeButton,
}: {
  selectedEvent: ReturnType<typeof useAppStore.getState>['selectedEvent'];
  linkedNotes: ReturnType<typeof useAppStore.getState>['notes'];
  linkedTasks: ReturnType<typeof useAppStore.getState>['tasks'];
  notes: ReturnType<typeof useAppStore.getState>['notes'];
  editingEvent: boolean;
  setEditingEvent: (v: boolean) => void;
  navigate: ReturnType<typeof useNavigate>;
  setSelectedNote: ReturnType<typeof useAppStore.getState>['setSelectedNote'];
  setReturnView: ReturnType<typeof useAppStore.getState>['setReturnView'];
  closeButton?: React.ReactNode;
}) {
  return (
    <>
      {/* Event Details */}
      <div className="island-pane context-inspector">
        <div className="section-header-row">
          <div className="section-label">CONTEXT INSPECTOR</div>
        </div>

        {selectedEvent ? (
          <div className="inspector-content">
            <div className="inspector-title-row">
              <h2 className="inspector-title">{selectedEvent.name}</h2>
              <button
                className="inspector-edit-btn"
                title="Edit event"
                onClick={() => setEditingEvent(true)}
              >
                <PencilIcon />
              </button>
            </div>

            <div className="inspector-details">
              <div className="detail-row">
                <ClockIcon />
                <span>
                  {formatEventDate(selectedEvent.from_)}{" "}
                  {formatEventTime(selectedEvent.from_)}
                  {" – "}
                  {formatEventTime(selectedEvent.to)}
                </span>
              </div>
              {selectedEvent.participants.length > 0 && (
                <div className="detail-row">
                  <UsersIcon />
                  <span>{selectedEvent.participants.join(", ")}</span>
                </div>
              )}
              {selectedEvent.description && (
                <div className="detail-row">
                  <DocumentIcon />
                  <span>{selectedEvent.description}</span>
                </div>
              )}
              {selectedEvent.metadata?.source_platform === 'google_calendar' && (
                <div className="detail-row source-info">
                  <span className="source-badge">🔗 Google Calendar</span>
                  {selectedEvent.metadata?.source_account && (
                    <span className="source-account">{selectedEvent.metadata.source_account}</span>
                  )}
                </div>
              )}
            </div>

            {/* Join Video Call intentionally hidden */}
          </div>
        ) : (
          <div className="inspector-content">
            <p style={{ color: "var(--text-tertiary)" }}>Select an event to inspect</p>
          </div>
        )}
      </div>

      {/* Linked Notes */}
      {linkedNotes.length > 0 && (
        <div className="island-pane linked-tasks-pane">
          <div className="section-label">LINKED NOTES</div>
          <div className="notes-grid notes-grid--compact">
            {linkedNotes.map((n) => (
              <NoteTile
                key={n.filename}
                note={n}
                onOpen={() => {
                  setSelectedNote(n);
                  setReturnView('/calendar');
                  navigate('/notes');
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Linked Tasks */}
      {linkedTasks.length > 0 && (
        <div className="island-pane linked-tasks-pane">
          <div className="section-label">LINKED TASKS</div>
          <div className="task-groups">
            {linkedTasks.map((t, i) => (
              <div key={i} className="task-item">
                <Checkbox
                  checked={t.completed}
                  onChange={() => toggleTask(t.source_file, t.line_number).catch(console.error)}
                />
                <span className={t.completed ? "completed" : ""}>{cleanTaskDisplay(t)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {editingEvent && selectedEvent && (
        <EventEditModal event={selectedEvent} onClose={() => setEditingEvent(false)} />
      )}
    </>
  );
}
