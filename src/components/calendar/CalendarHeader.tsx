import { ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon } from '../icons/Icons';

interface CalendarHeaderProps {
  monthYear: string;
  onPreviousWeek: () => void;
  onNextWeek: () => void;
  onToday: () => void;
}

export function CalendarHeader({ monthYear, onPreviousWeek, onNextWeek, onToday }: CalendarHeaderProps) {
  return (
    <div className="calendar-header">
      <div className="calendar-header-left">
        <div className="section-label">CALENDAR GRID</div>
        <h2 className="calendar-month">{monthYear}</h2>
      </div>
      <div className="calendar-header-right">
        <button className="view-dropdown">
          Weekly View
          <ChevronDownIcon />
        </button>
        <button className="today-btn" onClick={onToday}>
          Today
        </button>
        <div className="calendar-nav">
          <button className="nav-btn" onClick={onPreviousWeek} aria-label="Previous week">
            <ChevronLeftIcon />
          </button>
          <button className="nav-btn" onClick={onNextWeek} aria-label="Next week">
            <ChevronRightIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
