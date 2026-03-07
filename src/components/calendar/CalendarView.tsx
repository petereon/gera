import { useAppStore } from '../../stores/useAppStore';
import { useCalendarStore, VIEW_DAYS } from '../../stores/useCalendarStore';
import { useCalendarUtils } from '../../hooks/useCalendarUtils';
import { formatMonthYear } from '../../utils/dateFormatting';
import { CalendarHeader } from './CalendarHeader';
import { CalendarGrid } from './CalendarGrid';

interface CalendarViewProps {}

export function CalendarView({}: CalendarViewProps) {
  const events = useAppStore((state) => state.events);
  const notes = useAppStore((state) => state.notes);
  const currentPeriodStart = useCalendarStore((state) => state.currentPeriodStart);
  const calendarView = useCalendarStore((state) => state.calendarView);
  const setCalendarView = useCalendarStore((state) => state.setCalendarView);
  const goToPrevious = useCalendarStore((state) => state.goToPrevious);
  const goToNext = useCalendarStore((state) => state.goToNext);
  const goToToday = useCalendarStore((state) => state.goToToday);

  const { formatHour, hours, getEventForCell } = useCalendarUtils();

  const viewDays = VIEW_DAYS[calendarView];
  const visibleDates = Array.from({ length: viewDays }, (_, i) => {
    const d = new Date(currentPeriodStart);
    d.setDate(currentPeriodStart.getDate() + i);
    return d;
  });
  const visibleDayNames = visibleDates.map((d) =>
    d.toLocaleDateString('en', { weekday: 'short' })
  );
  const monthYear = visibleDates[0] ? formatMonthYear(visibleDates[0]) : '';

  return (
    <div className="calendar-pane">
      <CalendarHeader
        monthYear={monthYear}
        calendarView={calendarView}
        onViewChange={setCalendarView}
        onPrevious={goToPrevious}
        onNext={goToNext}
        onToday={goToToday}
      />
      <CalendarGrid
        dayNames={visibleDayNames}
        weekDates={visibleDates}
        hours={hours}
        formatHour={formatHour}
        events={events}
        notes={notes}
        getEventForCell={getEventForCell}
      />
    </div>
  );
}
