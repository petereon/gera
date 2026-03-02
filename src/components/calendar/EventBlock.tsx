import { EventEntity, NoteEntity } from '../../types';
import { useAppStore } from '../../stores/useAppStore';
import { calculateEventStyle } from '../../utils/eventPositioning';
import { formatEventTime } from '../../utils/dateFormatting';

interface EventBlockProps {
  event: EventEntity;
  notes: NoteEntity[];
}

export function EventBlock({ event, notes }: EventBlockProps) {
  const setSelectedEvent = useAppStore((state) => state.setSelectedEvent);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  
  const eventStyle = calculateEventStyle(event);

  const handleClick = () => {
    setSelectedEvent(event);
    const linkedNote = notes.find((n) => n.event_ids.includes(event.id));
    setSelectedNote(linkedNote ?? null);
  };

  return (
    <div
      className="event-block"
      onClick={handleClick}
      style={{ 
        cursor: "pointer",
        height: eventStyle.height,
        top: eventStyle.top,
        position: 'absolute',
        left: '4px',
        right: '4px',
      }}
    >
      <div className="event-title">{event.name}</div>
      <div className="event-time">
        {formatEventTime(event.from_)}
      </div>
    </div>
  );
}
