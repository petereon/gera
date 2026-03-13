import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { InboxIcon, CalendarIcon, DocumentIcon, ChevronLeftIcon, ChevronRightIcon, CogIcon } from '../icons/Icons';
import { useAppStore } from '../../stores/useAppStore';

interface SidebarProps {
  isPortrait?: boolean;
}

export function Sidebar({ isPortrait = false }: SidebarProps) {
  const [expanded, setExpanded] = useState(false);
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen);
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname.split('/')[1] || 'tasks';

  const containerClass = isPortrait
    ? 'left-column bottom-bar'
    : `left-column${expanded ? ' expanded' : ''}`;

  return (
    <>
      <div className={containerClass}>
        {/* Expand/collapse toggle — hidden in bottom-bar (portrait) mode */}
        {!isPortrait && (
          <button
            className="sidebar-toggle-btn"
            onClick={() => setExpanded(!expanded)}
            title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {expanded ? <ChevronLeftIcon /> : <ChevronRightIcon />}
          </button>
        )}

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

        {/* Settings island (spacer + settings button) */}
        <div className="sidebar-spacer"></div>
        <button
          className="sidebar-block sidebar-settings-btn"
          onClick={() => setSettingsOpen(true)}
          title="Settings"
        >
          <div className="sidebar-block-icon"><CogIcon /></div>
          <span className="sidebar-block-label">Settings</span>
        </button>
      </div>
    </>
  );
}
