/**
 * GeraRefChip component — renders Gera references as styled inline elements.
 *
 * Supports four kinds:
 * - event: @event-id (blue)
 * - datetime: @2026-03-01T09:00 (green)
 * - before: @before[2d]:event-id (orange)
 * - project: #project-id (purple)
 */

import { GeraRefKind } from './GeraRefNode';
import { ClockIcon } from '../components/icons/Icons';
import { formatEventDate, formatEventTime } from '../utils/dateFormatting';
import './GeraRefChip.css';

export interface GeraRefChipProps {
  kind: GeraRefKind;
  value: string;
  offset?: string;
  target?: string;
  datetime?: string;
  event?: string;
  project?: string;
}

/**
 * Renders a single Gera reference as a styled chip.
 * Used by GeraRefNode's decorate() method.
 */
export function GeraRefChip({
  kind,
  value,
  offset,
  target,
  datetime,
  event,
  project,
}: GeraRefChipProps): JSX.Element {
  // Determine the display text based on kind
  let displayText = value;

  switch (kind) {
    case 'event':
      displayText = event ? `@${event}` : value;
      break;
    case 'datetime':
      if (datetime) {
        const d = new Date(datetime);
        displayText = `${formatEventDate(d)} ${formatEventTime(d)}`;
      }
      break;
    case 'before':
      if (offset && target) {
        displayText = `@before[${offset}]:${target}`;
      }
      break;
    case 'project':
      displayText = project ? `#${project}` : value;
      break;
  }

  return (
    <span
      className={`gera-ref-chip gera-ref-chip--${kind}`}
      title={`Gera ${kind} reference`}
      contentEditable={false}
    >
      {kind === 'datetime' && <ClockIcon />}
      {displayText}
    </span>
  );
}
