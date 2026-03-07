import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { InboxIcon, CalendarIcon, DocumentIcon, ChevronLeftIcon, ChevronRightIcon } from '../icons/Icons';

export function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname.split('/')[1] || 'tasks';

  return (
    <div className={`left-column${expanded ? ' expanded' : ''}`}>
      {/* Expand/collapse toggle — visually distinct from nav islands */}
      <button
        className="sidebar-toggle-btn"
        onClick={() => setExpanded(!expanded)}
        title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {expanded ? <ChevronLeftIcon /> : <ChevronRightIcon />}
      </button>

      {/* Tasks island */}
      <div
        className={`sidebar-block ${currentPath === 'tasks' ? 'active' : ''}`}
        onClick={() => navigate('/tasks')}
      >
        <div className="sidebar-block-icon"><InboxIcon /></div>
        <span className="sidebar-block-label">Tasks</span>
      </div>

      {/* Notes island */}
      <div
        className={`sidebar-block ${currentPath === 'notes' ? 'active' : ''}`}
        onClick={() => navigate('/notes')}
      >
        <div className="sidebar-block-icon"><DocumentIcon /></div>
        <span className="sidebar-block-label">Notes</span>
      </div>

      {/* Calendar island */}
      <div
        className={`sidebar-block ${currentPath === 'calendar' ? 'active' : ''}`}
        onClick={() => navigate('/calendar')}
      >
        <div className="sidebar-block-icon"><CalendarIcon /></div>
        <span className="sidebar-block-label">Calendar</span>
      </div>
    </div>
  );
}
