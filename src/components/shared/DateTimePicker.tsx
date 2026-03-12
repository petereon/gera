import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import './DateTimePicker.css';

interface DateTimePickerProps {
  value: string;
  onChange: (v: string) => void;
  includeTime?: boolean;
  disabled?: boolean;
  placeholder?: string;
  clearable?: boolean;
  className?: string;
}

interface Parsed {
  year: number;
  month: number; // 0-indexed
  day: number;
  hour: number;
  minute: number;
}

function parseValue(val: string): Parsed | null {
  if (!val) return null;
  const parts = val.split('T');
  const dateParts = parts[0].split('-');
  if (dateParts.length < 3) return null;
  const year = parseInt(dateParts[0], 10);
  const month = parseInt(dateParts[1], 10) - 1;
  const day = parseInt(dateParts[2], 10);
  let hour = 9;
  let minute = 0;
  if (parts[1]) {
    const timeParts = parts[1].split(':');
    hour = parseInt(timeParts[0], 10) || 0;
    minute = parseInt(timeParts[1], 10) || 0;
  }
  return { year, month, day, hour, minute };
}

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function buildValue(p: Parsed, includeTime: boolean): string {
  const date = `${p.year}-${pad2(p.month + 1)}-${pad2(p.day)}`;
  if (!includeTime) return date;
  return `${date}T${pad2(p.hour)}:${pad2(p.minute)}`;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const SHORT_MONTH = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function formatDisplay(val: string, includeTime: boolean): string {
  const p = parseValue(val);
  if (!p) return '';
  const date = `${SHORT_MONTH[p.month]} ${p.day}, ${p.year}`;
  if (!includeTime) return date;
  return `${date} \u00b7 ${pad2(p.hour)}:${pad2(p.minute)}`;
}

function CalendarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="3" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M2 6.5h12" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5.5 1.5v2M10.5 1.5v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function DateTimePicker({
  value,
  onChange,
  includeTime = true,
  disabled = false,
  placeholder = '',
  clearable = false,
  className,
}: DateTimePickerProps) {
  const [open, setOpen] = useState(false);
  const [popoverStyle, setPopoverStyle] = useState<React.CSSProperties>({});

  const parsed = parseValue(value);
  const today = new Date();

  const [viewYear, setViewYear] = useState(parsed?.year ?? today.getFullYear());
  const [viewMonth, setViewMonth] = useState(parsed?.month ?? today.getMonth());

  // Sync view when value changes externally
  useEffect(() => {
    const p = parseValue(value);
    if (p) {
      setViewYear(p.year);
      setViewMonth(p.month);
    }
  }, [value]);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Position popover below (or above) the trigger
  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const popoverHeight = 340; // approximate
    const popoverWidth = 264;
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const spaceAbove = rect.top - 8;

    let top: number;
    if (spaceBelow >= popoverHeight || spaceBelow >= spaceAbove) {
      top = rect.bottom + 4;
    } else {
      top = rect.top - popoverHeight - 4;
    }

    let left = rect.left;
    if (left + popoverWidth > window.innerWidth - 8) {
      left = rect.right - popoverWidth;
    }

    setPopoverStyle({ top, left });
  };

  const openPopover = () => {
    updatePosition();
    setOpen(true);
  };

  // Close on outside click (mousedown) or Escape
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (
        popoverRef.current && !popoverRef.current.contains(e.target as Node) &&
        triggerRef.current && !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  // Calendar grid
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstDow = new Date(viewYear, viewMonth, 1).getDay(); // 0=Sun

  const handleDayClick = (day: number) => {
    const existing = parseValue(value);
    const hour = existing?.hour ?? 9;
    const minute = existing?.minute ?? 0;
    const next: Parsed = { year: viewYear, month: viewMonth, day, hour, minute };
    const built = buildValue(next, includeTime);
    onChange(built);
    if (!includeTime) {
      setOpen(false);
    }
  };

  const handleHourChange = (delta: number) => {
    if (!parsed) return;
    const next = { ...parsed, hour: ((parsed.hour + delta) + 24) % 24 };
    onChange(buildValue(next, true));
  };

  const handleMinuteChange = (delta: number) => {
    if (!parsed) return;
    const next = { ...parsed, minute: ((parsed.minute + delta * 5) + 60) % 60 };
    onChange(buildValue(next, true));
  };

  const todayYear = today.getFullYear();
  const todayMonth = today.getMonth();
  const todayDay = today.getDate();

  const displayLabel = formatDisplay(value, includeTime);

  const popover = (
    <div ref={popoverRef} className="dtp-popover" style={popoverStyle}>
      {/* Month navigation */}
      <div className="dtp-nav">
        <button
          type="button"
          className="dtp-nav__btn"
          onClick={() => {
            if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
            else setViewMonth((m) => m - 1);
          }}
        >
          &#8249;
        </button>
        <span className="dtp-nav__label">{MONTH_NAMES[viewMonth]} {viewYear}</span>
        <button
          type="button"
          className="dtp-nav__btn"
          onClick={() => {
            if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
            else setViewMonth((m) => m + 1);
          }}
        >
          &#8250;
        </button>
      </div>

      {/* Day-of-week headers */}
      <div className="dtp-grid">
        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => (
          <div key={d} className="dtp-dow">{d}</div>
        ))}

        {/* Leading empty cells */}
        {Array.from({ length: firstDow }).map((_, i) => (
          <div key={`e-${i}`} className="dtp-day dtp-day--empty" />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const isToday = viewYear === todayYear && viewMonth === todayMonth && day === todayDay;
          const isSelected = parsed
            ? parsed.year === viewYear && parsed.month === viewMonth && parsed.day === day
            : false;
          let cls = 'dtp-day';
          if (isSelected) cls += ' dtp-day--selected';
          else if (isToday) cls += ' dtp-day--today';
          return (
            <button
              key={day}
              type="button"
              className={cls}
              onClick={() => handleDayClick(day)}
            >
              {day}
            </button>
          );
        })}
      </div>

      {/* Time section */}
      {includeTime && (
        <div className="dtp-time">
          {/* Hour spinner */}
          <div className="dtp-spinner">
            <button
              type="button"
              className="dtp-spinner__btn"
              disabled={!parsed}
              onClick={() => handleHourChange(1)}
            >
              &#9650;
            </button>
            <span className="dtp-spinner__val">
              {parsed ? pad2(parsed.hour) : '--'}
            </span>
            <button
              type="button"
              className="dtp-spinner__btn"
              disabled={!parsed}
              onClick={() => handleHourChange(-1)}
            >
              &#9660;
            </button>
          </div>

          <span className="dtp-time__colon">:</span>

          {/* Minute spinner */}
          <div className="dtp-spinner">
            <button
              type="button"
              className="dtp-spinner__btn"
              disabled={!parsed}
              onClick={() => handleMinuteChange(1)}
            >
              &#9650;
            </button>
            <span className="dtp-spinner__val">
              {parsed ? pad2(parsed.minute) : '--'}
            </span>
            <button
              type="button"
              className="dtp-spinner__btn"
              disabled={!parsed}
              onClick={() => handleMinuteChange(-1)}
            >
              &#9660;
            </button>
          </div>
        </div>
      )}

      {/* Done button */}
      {includeTime && (
        <div className="dtp-done-row">
          <button
            type="button"
            className="dtp-done-btn"
            onClick={() => setOpen(false)}
          >
            Done
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={`dtp-trigger${open ? ' dtp-trigger--open' : ''}${className ? ` ${className}` : ''}`}
        disabled={disabled}
        onClick={openPopover}
      >
        <span className={`dtp-trigger__label${!displayLabel ? ' dtp-trigger__label--placeholder' : ''}`}>
          {displayLabel || placeholder || 'Select date'}
        </span>
        {clearable && value ? (
          <span
            className="dtp-trigger__clear"
            role="button"
            aria-label="Clear date"
            onClick={(e) => { e.stopPropagation(); onChange(''); setOpen(false); }}
          >
            ×
          </span>
        ) : (
          <span className="dtp-trigger__icon">
            <CalendarIcon />
          </span>
        )}
      </button>
      {open && createPortal(popover, document.body)}
    </>
  );
}
