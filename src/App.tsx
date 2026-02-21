import React, { useCallback, useEffect, useState } from "react";
import "./App.css";
import { listen } from "@tauri-apps/api/event";
import { MarkdownPreview } from "./MarkdownPreview";
import {
  listEvents,
  listNotes,
  listFloatingTasks,
  type EventEntity,
  type NoteEntity,
  type TaskEntity,
} from "./api";

// Icons
const InboxIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
  </svg>
);

const CalendarIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const ProjectsIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const TagsIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
    <line x1="7" y1="7" x2="7.01" y2="7" />
  </svg>
);

const ChevronLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const VideoIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polygon points="23 7 16 12 23 17 23 7" />
    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
  </svg>
);

const ClockIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const UsersIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const MoreIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="1" />
    <circle cx="19" cy="12" r="1" />
    <circle cx="5" cy="12" r="1" />
  </svg>
);

const PlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const DocumentIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

function App() {
  const [activeNav, setActiveNav] = useState("calendar");
  const [draggedNote, setDraggedNote] = useState<string | null>(null);

  // --- Live data from backend ---
  const [events, setEvents] = useState<EventEntity[]>([]);
  const [notes, setNotes] = useState<NoteEntity[]>([]);
  const [tasks, setTasks] = useState<TaskEntity[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<EventEntity | null>(null);
  const [selectedNote, setSelectedNote] = useState<NoteEntity | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadData = useCallback(async () => {
    try {
      const [ev, nt, tk] = await Promise.all([
        listEvents(),
        listNotes(),
        listFloatingTasks(),
      ]);
      setEvents(ev);
      setNotes(nt);
      setTasks(tk);
    } catch (err) {
      console.error("Failed to load data:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    reloadData().then(() => setLoading(false));
  }, [reloadData]);

  // Re-load when the file-system watcher fires
  useEffect(() => {
    const unlisten = listen<{ changes: { type: string; path: string }[] }>(
      "gera://fs-changed",
      () => {
        reloadData();
      },
    );
    return () => {
      unlisten.then((fn) => fn());
    };
  }, [reloadData]);

  // Floating notes = notes without event_ids
  const floatingNotes = notes.filter((n) => n.event_ids.length === 0);

  // Find notes linked to the selected event
  const linkedNotes = selectedEvent
    ? notes.filter((n) => n.event_ids.includes(selectedEvent.id))
    : [];

  // Derive calendar week helpers
  const getWeekDates = () => {
    const now = new Date();
    const monday = new Date(now);
    monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d;
    });
  };

  const weekDates = getWeekDates();
  const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const hours = Array.from({ length: 10 }, (_, i) => i + 8); // 8 AM – 5 PM

  const formatHour = (h: number) => {
    const suffix = h >= 12 ? "PM" : "AM";
    const display = h > 12 ? h - 12 : h === 0 ? 12 : h;
    return `${display} ${suffix}`;
  };

  // Place events onto the grid
  const getEventForCell = (hourIndex: number, dayIndex: number) => {
    const cellDate = weekDates[dayIndex];
    const cellHour = hours[hourIndex];
    return events.filter((ev) => {
      try {
        const from = new Date(ev.from_);
        return (
          from.getFullYear() === cellDate.getFullYear() &&
          from.getMonth() === cellDate.getMonth() &&
          from.getDate() === cellDate.getDate() &&
          from.getHours() === cellHour
        );
      } catch {
        return false;
      }
    });
  };

  const monthYear = weekDates[0]
    ? weekDates[0].toLocaleDateString("en-US", { month: "long", year: "numeric" })
    : "";

  if (loading) {
    return (
      <div className="app-container" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-tertiary)", fontSize: 16 }}>Loading workspace…</div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* LEFT COLUMN */}
      <div className="left-column">
        {/* STAGING AREA */}
        <div className="island-pane staging-area">
          <div className="section-label">STAGING AREA</div>
          <nav className="staging-nav">
            <button
              className={`staging-btn ${activeNav === "inbox" ? "active" : ""}`}
              onClick={() => setActiveNav("inbox")}
            >
              <InboxIcon />
              {floatingNotes.length > 0 && (
                <span className="staging-badge">{floatingNotes.length}</span>
              )}
            </button>
            <button
              className={`staging-btn ${activeNav === "calendar" ? "active" : ""}`}
              onClick={() => setActiveNav("calendar")}
            >
              <CalendarIcon />
            </button>
            <button
              className={`staging-btn ${activeNav === "projects" ? "active" : ""}`}
              onClick={() => setActiveNav("projects")}
            >
              <ProjectsIcon />
            </button>
            <button
              className={`staging-btn ${activeNav === "tags" ? "active" : ""}`}
              onClick={() => setActiveNav("tags")}
            >
              <TagsIcon />
            </button>
          </nav>
          <div className="staging-labels">
            <span>Inbox</span>
            <span>Calendar</span>
            <span>Projects</span>
            <span>Tags</span>
          </div>
        </div>

        {/* FLOATING NOTES */}
        <div className="island-pane floating-notes">
          <div className="section-header-row">
            <div className="section-label">FLOATING NOTES</div>
            <button className="icon-btn"><MoreIcon /></button>
          </div>
          <div className="notes-grid">
            {floatingNotes.length === 0 && (
              <div className="empty-state">No floating notes yet</div>
            )}
            {floatingNotes.map((note) => (
              <div
                key={note.filename}
                className={`note-card medium ${draggedNote === note.filename ? "dragging" : ""}`}
                draggable
                onDragStart={() => setDraggedNote(note.filename)}
                onDragEnd={() => setDraggedNote(null)}
                onClick={() => setSelectedNote(note)}
              >
                <div className="note-title">{note.title}</div>
                <div className="note-body">{note.body_preview}</div>
              </div>
            ))}
          </div>
        </div>

        {/* FLOATING TASKS */}
        {tasks.length > 0 && (
          <div className="island-pane floating-tasks-pane">
            <div className="section-label">FLOATING TASKS</div>
            <div className="task-groups">
              {tasks.map((t, i) => (
                <div key={i} className="task-item">
                  <div className={`checkbox ${t.completed ? "checked" : ""}`}>
                    {t.completed && <CheckIcon />}
                  </div>
                  <span className={t.completed ? "completed" : ""}>{t.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* QUICK CAPTURE */}
        <div className="island-pane quick-capture">
          <div className="section-label">Quick Capture</div>
          <div className="capture-input-wrapper">
            <input
              type="text"
              className="capture-input"
              placeholder="Type a note..."
            />
            <button className="capture-add-btn">
              <PlusIcon />
            </button>
          </div>
        </div>
      </div>

      {/* CENTER COLUMN - CALENDAR */}
      <main className="island-pane calendar-pane">
        <div className="calendar-header">
          <div className="calendar-header-left">
            <div className="section-label">CALENDAR GRID</div>
            <h2 className="calendar-month">{monthYear}</h2>
          </div>
          <div className="calendar-header-right">
            <button className="view-dropdown">
              Weekly View
              <ChevronDownIcon />
            </button>
            <div className="calendar-nav">
              <button className="nav-btn"><ChevronLeftIcon /></button>
              <button className="nav-btn"><ChevronRightIcon /></button>
            </div>
          </div>
        </div>

        <div className="calendar-grid">
          {/* Day headers row */}
          <div className="calendar-corner"></div>
          {dayNames.map((day, i) => (
            <div key={day} className="day-header">
              <span className="day-name">{day}</span>
              <span className="day-number">{weekDates[i].getDate()}</span>
            </div>
          ))}

          {/* Time rows */}
          {hours.map((hour, hourIndex) => (
            <React.Fragment key={`row-${hourIndex}`}>
              <div className="time-cell">
                {formatHour(hour)}
              </div>
              {dayNames.map((_, dayIndex) => {
                const cellEvents = getEventForCell(hourIndex, dayIndex);
                return (
                  <div key={`cell-${hourIndex}-${dayIndex}`} className="grid-cell">
                    {cellEvents.map((ev) => (
                      <div
                        key={ev.id}
                        className="event-block"
                        onClick={() => {
                          setSelectedEvent(ev);
                          // Also select the first linked note if any
                          const linked = notes.find((n) =>
                            n.event_ids.includes(ev.id)
                          );
                          setSelectedNote(linked ?? null);
                        }}
                        style={{ cursor: "pointer" }}
                      >
                        <div className="event-title">{ev.name}</div>
                        <div className="event-time">
                          {new Date(ev.from_).toLocaleTimeString("en-US", {
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </main>

      {/* RIGHT COLUMN - CONTEXT INSPECTOR */}
      <div className="right-column">
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
                    {new Date(selectedEvent.from_).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}{" "}
                    {new Date(selectedEvent.from_).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                    {" – "}
                    {new Date(selectedEvent.to).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                    })}
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

        {/* Linked notes for the selected event */}
        {linkedNotes.length > 0 && (
          <div className="island-pane linked-tasks-pane">
            <div className="section-label">LINKED NOTES</div>
            <div className="task-groups">
              {linkedNotes.map((n) => (
                <div
                  key={n.filename}
                  className="task-item"
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelectedNote(n)}
                >
                  <DocumentIcon />
                  <span>{n.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Note preview */}
        {selectedNote && (
          <div className="island-pane note-preview-pane">
            <div className="section-label">NOTE PREVIEW</div>
            <MarkdownPreview
              content={selectedNote.raw_content}
              showTitle
              showMeta
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
