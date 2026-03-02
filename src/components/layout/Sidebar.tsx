import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/useAppStore';
import { useNoteFiltering } from '../../hooks/useNoteFiltering';
import { InboxIcon, CalendarIcon, ProjectsIcon, DocumentIcon } from '../icons/Icons';

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname.split('/')[1] || 'tasks';
  
  const tasks = useAppStore((state) => state.tasks);
  const notes = useAppStore((state) => state.notes);

  // Calculate floating notes for badge
  const { floatingNotes } = useNoteFiltering(notes, "");

  const handleNavClick = (view: string) => {
    navigate(`/${view}`);
  };

  return (
    <div className="left-column">
      {/* Tasks Block */}
      <div
        className={`sidebar-block ${currentPath === "tasks" ? "active" : ""}`}
        onClick={() => handleNavClick("tasks")}
      >
        <div className="sidebar-block-icon">
          <InboxIcon />
        </div>
        <div className="sidebar-block-label">Tasks</div>
        {tasks.length > 0 && (
          <div className="sidebar-block-badge">{tasks.length}</div>
        )}
      </div>

      {/* Calendar Block */}
      <div
        className={`sidebar-block ${currentPath === "calendar" ? "active" : ""}`}
        onClick={() => handleNavClick("calendar")}
      >
        <div className="sidebar-block-icon">
          <CalendarIcon />
        </div>
        <div className="sidebar-block-label">Calendar</div>
      </div>

      {/* Projects Block */}
      <div
        className={`sidebar-block ${currentPath === "projects" ? "active" : ""}`}
        onClick={() => handleNavClick("projects")}
      >
        <div className="sidebar-block-icon">
          <ProjectsIcon />
        </div>
        <div className="sidebar-block-label">Projects</div>
      </div>

      {/* Notes Block */}
      <div
        className={`sidebar-block ${currentPath === "notes" ? "active" : ""}`}
        onClick={() => handleNavClick("notes")}
      >
        <div className="sidebar-block-icon">
          <DocumentIcon />
        </div>
        <div className="sidebar-block-label">Notes</div>
        {floatingNotes.length > 0 && (
          <div className="sidebar-block-badge">{floatingNotes.length}</div>
        )}
      </div>
    </div>
  );
}
