import { useState } from 'react';
import { EventEntity, NoteEntity } from '../../types';
import { useAppStore } from '../../stores/useAppStore';
import { calculateEventStyle } from '../../utils/eventPositioning';
import { formatEventTime } from '../../utils/dateFormatting';
import { EventEditModal } from './EventEditModal';

interface EventBlockProps {
  event: EventEntity;
  notes: NoteEntity[];
}

export function EventBlock({ event, notes }: EventBlockProps) {
  const setSelectedEvent = useAppStore((state) => state.setSelectedEvent);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  const [editing, setEditing] = useState(false);
  
  const eventStyle = calculateEventStyle(event);
  // Only show time if the block is tall enough to fit a second line (~44px = ~30min)
  const heightPx = parseFloat(eventStyle.height);
  const showTime = heightPx >= 44;

  const handleClick = () => {
    setSelectedEvent(event);
    const linkedNote = notes.find((n) => n.event_ids.includes(event.id));
    setSelectedNote(linkedNote ?? null);
  };

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditing(true);
  };

  // Determine source badge
  const isGoogleCalendar = event.metadata?.source_platform === 'google_calendar';
  const sourceBadge = isGoogleCalendar ? (
    <div className="event-source-badge event-source-badge--google" title="From Google Calendar">
      G
    </div>
  ) : null;

  return (
    <>
      <div
        className="event-block"
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        style={{ 
          cursor: "pointer",
          height: eventStyle.height,
          top: eventStyle.top,
          position: 'absolute',
          left: '4px',
          right: '4px',
        }}
      >
        <div className="event-block-content">
          <div className="event-title">{event.name}</div>
          {showTime && (
            <div className="event-time">
              {formatEventTime(event.from_)}
            </div>
          )}
        </div>
        {sourceBadge}
      </div>

      {editing && (
        <EventEditModal
          event={event}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}

