import React from 'react';
import { EventEntity, NoteEntity } from '../../types';
import { EventBlock } from './EventBlock';

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
  getEventForCell 
}: CalendarGridProps) {
  return (
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
            const cellEvents = getEventForCell(events, hourIndex, dayIndex, weekDates);
            return (
              <div key={`cell-${hourIndex}-${dayIndex}`} className="grid-cell">
                {cellEvents.map((ev) => (
                  <EventBlock key={ev.id} event={ev} notes={notes} />
                ))}
              </div>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}
