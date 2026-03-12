import React, { useState } from 'react';
import { EventEntity, NoteEntity } from '../../types';
import { getAllDayEventsForDay } from '../../utils/eventPositioning';
import { useAppStore } from '../../stores/useAppStore';
import { EventBlock } from './EventBlock';
import EventCreateModal from './EventCreateModal';

interface CalendarGridProps {
  dayNames: string[];
  weekDates: Date[];
  hours: number[];
  formatHour: (hour: number) => string;
  events: EventEntity[];
  notes: NoteEntity[];
  getEventForCell: (
    events: EventEntity[],
    hourIndex: number,
    dayIndex: number,
    weekDates: Date[]
  ) => EventEntity[];
}

export function CalendarGrid({
  dayNames,
  weekDates,
  hours,
  formatHour,
  events,
  notes,
  getEventForCell,
}: CalendarGridProps) {
  const [creating, setCreating] = useState(false);
  const [createFromIso, setCreateFromIso] = useState('');
  const [createToIso, setCreateToIso] = useState('');
  const colCount = weekDates.length;
  const gridStyle = {
    gridTemplateColumns: `60px repeat(${colCount}, 1fr)`,
  };
  const setSelectedEvent = useAppStore((s) => s.setSelectedEvent);
  const setSelectedNote = useAppStore((s) => s.setSelectedNote);

  return (
    <div className="calendar-grid" style={gridStyle}>
      {/* Day headers row */}
      <div className="calendar-corner"></div>
      {dayNames.map((day, i) => {
        const allDayEvs = getAllDayEventsForDay(events, weekDates[i]);
        return (
          <div key={day + i} className="day-header">
            <span className="day-name">{day}</span>
            <span className="day-number">{weekDates[i].getDate()}</span>
            {allDayEvs.length > 0 && (
              <div className="all-day-chips">
                {allDayEvs.map((ev) => (
                  <div
                    key={ev.id}
                    className="all-day-chip"
                    title={ev.name}
                    onClick={() => {
                      setSelectedEvent(ev);
                      const linkedNote = notes.find((n) => n.event_ids.includes(ev.id));
                      setSelectedNote(linkedNote ?? null);
                    }}
                  >
                    {ev.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {/* Time rows */}
      {hours.map((hour, hourIndex) => (
        <React.Fragment key={`row-${hourIndex}`}>
          <div className="time-cell">
            {formatHour(hour)}
          </div>
          {dayNames.map((_, dayIndex) => {
            const cellEvents = getEventForCell(events, hourIndex, dayIndex, weekDates);
            const handleCellClick = () => {
              if (cellEvents.length > 0) return;
              const base = new Date(weekDates[dayIndex]);
              base.setHours(hours[hourIndex], 0, 0, 0);
              const end = new Date(base);
              end.setHours(base.getHours() + 1);
              const pad = (n: number) => String(n).padStart(2, '0');
              const toLocalIso = (d: Date) => {
                return (
                  d.getFullYear() + '-' +
                  pad(d.getMonth() + 1) + '-' +
                  pad(d.getDate()) + 'T' +
                  pad(d.getHours()) + ':' +
                  pad(d.getMinutes()) + ':' +
                  pad(d.getSeconds())
                );
              };

              setCreateFromIso(toLocalIso(base));
              setCreateToIso(toLocalIso(end));
              setCreating(true);
            };

            return (
              <div key={`cell-${hourIndex}-${dayIndex}`} className="grid-cell" onClick={handleCellClick}>
                {cellEvents.map((ev) => (
                  <EventBlock key={ev.id} event={ev} notes={notes} />
                ))}
              </div>
            );
          })}
        </React.Fragment>
      ))}
      {creating && (
        <EventCreateModal
          fromIso={createFromIso}
          toIso={createToIso}
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );
}
