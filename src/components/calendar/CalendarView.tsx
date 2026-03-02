import { useAppStore } from '../../stores/useAppStore';
import { useCalendarUtils } from '../../hooks/useCalendarUtils';
import { formatMonthYear } from '../../utils/dateFormatting';
import { CalendarHeader } from './CalendarHeader';
import { CalendarGrid } from './CalendarGrid';

interface CalendarViewProps {}

export function CalendarView({}: CalendarViewProps) {
  const events = useAppStore((state) => state.events);
  const notes = useAppStore((state) => state.notes);

  const { getWeekDates, formatHour, dayNames, hours, getEventForCell } = useCalendarUtils();

  const weekDates = getWeekDates();
  const monthYear = weekDates[0] ? formatMonthYear(weekDates[0]) : "";

  return (
    <div className="calendar-pane">
      <CalendarHeader monthYear={monthYear} />
      <CalendarGrid
        dayNames={dayNames}
        weekDates={weekDates}
        hours={hours}
        formatHour={formatHour}
        events={events}
        notes={notes}
        getEventForCell={getEventForCell}
      />
    </div>
  );
}
