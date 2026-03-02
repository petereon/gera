import { EventEntity } from '../api';

export const HOUR_HEIGHT_PX = 56;

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
