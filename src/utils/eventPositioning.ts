import { EventEntity } from '../api';

export const HOUR_HEIGHT_PX = 56;

/** True if the event spans 24 hours or more (all-day / multi-day). */
export function isAllDayEvent(event: EventEntity): boolean {
  try {
    const durationMs = new Date(event.to).getTime() - new Date(event.from_).getTime();
    return durationMs >= 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

/** Return all-day events that overlap a given calendar column date. */
export function getAllDayEventsForDay(events: EventEntity[], day: Date): EventEntity[] {
  const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
  const dayEnd = dayStart + 24 * 60 * 60 * 1000;
  return events.filter((ev) => {
    if (!isAllDayEvent(ev)) return false;
    try {
      const from = new Date(ev.from_).getTime();
      const to = new Date(ev.to).getTime();
      return from < dayEnd && to > dayStart;
    } catch {
      return false;
    }
  });
}

export interface EventStyle {
  height: string;
  top: string;
}

/**
 * Calculate CSS height and top positioning for an event block in the calendar grid.
 * Height is based on event duration, and top is based on minute offset within the hour.
 */
export function calculateEventStyle(event: EventEntity): EventStyle {
  try {
    const from = new Date(event.from_);
    const to = new Date(event.to);
    
    // Duration in hours (decimal)
    const durationMs = to.getTime() - from.getTime();
    const durationHours = durationMs / (1000 * 60 * 60);
    
    // Offset within the hour (for minute positioning)
    const minuteOffset = from.getMinutes();
    const minuteOffsetPercent = (minuteOffset / 60) * 100;
    
    // Height calculation (56px per hour as per grid-cell min-height)
    const height = durationHours * HOUR_HEIGHT_PX;
    
    return {
      height: `${height}px`,
      top: `${minuteOffsetPercent}%`,
    };
  } catch {
    return {
      height: `${HOUR_HEIGHT_PX}px`,
      top: '0',
    };
  }
}
