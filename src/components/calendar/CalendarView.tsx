import { useAppStore } from '../../stores/useAppStore';
import { useCalendarStore } from '../../stores/useCalendarStore';
import { useCalendarUtils } from '../../hooks/useCalendarUtils';
import { formatMonthYear } from '../../utils/dateFormatting';
import { CalendarHeader } from './CalendarHeader';
import { CalendarGrid } from './CalendarGrid';

interface CalendarViewProps {}

export function CalendarView({}: CalendarViewProps) {
  const events = useAppStore((state) => state.events);
  const notes = useAppStore((state) => state.notes);
  const currentWeekStart = useCalendarStore((state) => state.currentWeekStart);
  const goToPreviousWeek = useCalendarStore((state) => state.goToPreviousWeek);
  const goToNextWeek = useCalendarStore((state) => state.goToNextWeek);
  const goToToday = useCalendarStore((state) => state.goToToday);

  const { getWeekDates, formatHour, dayNames, hours, getEventForCell } = useCalendarUtils();

  const weekDates = getWeekDates(currentWeekStart);
  const monthYear = weekDates[0] ? formatMonthYear(weekDates[0]) : "";

  return (
    <div className="calendar-pane">
      <CalendarHeader 
        monthYear={monthYear}
        onPreviousWeek={goToPreviousWeek}
        onNextWeek={goToNextWeek}
        onToday={goToToday}
      />
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
