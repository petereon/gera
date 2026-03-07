import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../stores/useAppStore';
import { 
  VideoIcon, 
  ClockIcon, 
  UsersIcon, 
  MoreIcon, 
  DocumentIcon 
} from '../icons/Icons';
import { Checkbox } from '../shared/Checkbox';
import { NoteTile } from '../notes/NoteTile';
import { cleanTaskDisplay } from '../../utils/taskFormatting';
import { formatEventDate, formatEventTime } from '../../utils/dateFormatting';
import { toggleTask } from '../../api';

interface InspectorProps {
  isVisible: boolean;
}

export function Inspector({ isVisible }: InspectorProps) {
  const navigate = useNavigate();
  const selectedEvent = useAppStore((state) => state.selectedEvent);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  const setReturnView = useAppStore((state) => state.setReturnView);
  const notes = useAppStore((state) => state.notes);
  const tasks = useAppStore((state) => state.tasks);

  const linkedNotes = selectedEvent
    ? notes.filter((n) => n.event_ids.includes(selectedEvent.id))
    : [];

  const linkedTasks = selectedEvent
    ? tasks.filter((t) => t.event_ids.includes(selectedEvent.id))
    : [];

  if (!isVisible) {
    return null;
  }

  return (
    <div className="right-column">
      {/* Event Details */}
      <div className="island-pane context-inspector">
        <div className="section-header-row">
          <div className="section-label">CONTEXT INSPECTOR</div>
          <button className="icon-btn"><MoreIcon /></button>
        </div>

        {selectedEvent ? (
          <div className="inspector-content">
            <h2 className="inspector-title">{selectedEvent.name}</h2>
            <span className="editable-badge">(Editable)</span>

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
            </div>

            <button className="btn-primary">
              <VideoIcon />
              Join Video Call
            </button>
          </div>
        ) : (
          <div className="inspector-content">
            <p style={{ color: "var(--text-tertiary)" }}>Select an event to inspect</p>
          </div>
        )}
      </div>

      {/* Linked Notes — shown as tiles, click navigates to notes view */}
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

    </div>
  );
}
