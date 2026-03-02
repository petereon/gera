import { ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon } from '../icons/Icons';

interface CalendarHeaderProps {
  monthYear: string;
}

export function CalendarHeader({ monthYear }: CalendarHeaderProps) {
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
        <div className="calendar-nav">
          <button className="nav-btn"><ChevronLeftIcon /></button>
          <button className="nav-btn"><ChevronRightIcon /></button>
        </div>
      </div>
    </div>
  );
}
