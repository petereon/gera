# Gera UI Refactoring Plan

## Overview

Refactor the monolithic `App.tsx` (727 lines) into a well-structured, maintainable component architecture using Zustand for state management.

## State Management with Zustand

### Why Zustand?

- Minimal boilerplate compared to Redux
- No context provider wrapper needed
- TypeScript-friendly
- Perfect for our needs: view state, search filters, selections, and data cache

### Installation

```bash
bun add zustand
```

### Store Structure

```typescript
// src/stores/useAppStore.ts
interface AppStore {
  // Navigation
  activeView: 'tasks' | 'calendar' | 'projects' | 'notes';
  setActiveView: (view: string) => void;
  
  // Data
  events: EventEntity[];
  notes: NoteEntity[];
  tasks: TaskEntity[];
  loading: boolean;
  setEvents: (events: EventEntity[]) => void;
  setNotes: (notes: NoteEntity[]) => void;
  setTasks: (tasks: TaskEntity[]) => void;
  setLoading: (loading: boolean) => void;
  reloadData: () => Promise<void>;
  
  // Selections
  selectedEvent: EventEntity | null;
  selectedNote: NoteEntity | null;
  setSelectedEvent: (event: EventEntity | null) => void;
  setSelectedNote: (note: NoteEntity | null) => void;
  
  // Search filters
  tasksSearch: string;
  notesSearch: string;
  projectsSearch: string;
  setTasksSearch: (search: string) => void;
  setNotesSearch: (search: string) => void;
  setProjectsSearch: (search: string) => void;
}
```

```typescript
// src/stores/useCalendarStore.ts
interface CalendarStore {
  currentWeekStart: Date;
  setCurrentWeekStart: (date: Date) => void;
  goToPreviousWeek: () => void;
  goToNextWeek: () => void;
  goToToday: () => void;
}
```

## Folder Structure

```
src/
├── api.ts                    (keep as-is - already good)
├── main.tsx                  (keep as-is - entry point)
├── App.tsx                   (slim down to ~50 lines - shell only)
├── App.css                   (keep for now, split later)
├── MarkdownPreview.tsx       (keep as-is)
├── stores/
│   ├── useAppStore.ts        (main app state with Zustand)
│   └── useCalendarStore.ts   (calendar-specific state)
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx       (navigation sidebar with blocks)
│   │   ├── MainContent.tsx   (view container/router)
│   │   └── Inspector.tsx     (right column for calendar)
│   ├── calendar/
│   │   ├── CalendarView.tsx  (main calendar component)
│   │   ├── CalendarGrid.tsx  (grid with events)
│   │   ├── CalendarHeader.tsx (month/nav controls)
│   │   ├── EventBlock.tsx    (individual event)
│   │   └── DayHeader.tsx     (sticky day labels)
│   ├── tasks/
│   │   ├── TasksView.tsx     (main tasks component)
│   │   ├── TaskList.tsx      (scrollable list)
│   │   ├── TaskGroup.tsx     (event group with tasks)
│   │   ├── TaskItem.tsx      (individual task)
│   │   └── TaskSearch.tsx    (search input)
│   ├── notes/
│   │   ├── NotesView.tsx     (main notes component)
│   │   ├── NotesGrid.tsx     (tile grid)
│   │   ├── NoteTile.tsx      (individual tile)
│   │   └── NoteSearch.tsx    (search input)
│   ├── projects/
│   │   ├── ProjectsView.tsx  (main projects component)
│   │   ├── ProjectsGrid.tsx  (tile grid)
│   │   ├── ProjectTile.tsx   (individual tile)
│   │   └── ProjectSearch.tsx (search input)
│   ├── shared/
│   │   ├── Checkbox.tsx      (task checkbox)
│   │   ├── SearchInput.tsx   (reusable search)
│   │   ├── Tag.tsx           (event/project tags)
│   │   └── EmptyState.tsx    (empty state message)
│   └── icons/
│       └── Icons.tsx         (all SVG icon components)
├── hooks/
│   ├── useGeraSync.ts        (data fetching & fs-changed listener)
│   ├── useTaskFiltering.ts   (task search & filter logic)
│   ├── useNoteFiltering.ts   (note search & filter logic)
│   └── useCalendarUtils.ts   (date calculations, event positioning)
├── types/
│   └── index.ts              (re-export from api.ts + local types)
├── utils/
│   ├── taskFormatting.ts     (task text cleanup logic)
│   ├── dateFormatting.ts     (date/time display helpers)
│   └── eventPositioning.ts   (event size/position calculations)
└── styles/
    ├── variables.css         (design tokens only)
    ├── layout.css            (grid & layout)
    ├── components.css        (shared component styles)
    └── views.css             (view-specific styles)
```

## File Responsibilities

### Core Files

#### `App.tsx` (~50 lines)
```typescript
import { useAppStore } from './stores/useAppStore';
import { useGeraSync } from './hooks/useGeraSync';
import Sidebar from './components/layout/Sidebar';
import MainContent from './components/layout/MainContent';
import Inspector from './components/layout/Inspector';

function App() {
  const activeView = useAppStore(state => state.activeView);
  const loading = useAppStore(state => state.loading);
  
  // Setup data sync and fs-changed listener
  useGeraSync();
  
  if (loading) {
    return <LoadingState />;
  }
  
  return (
    <div className={`app-container ${activeView !== 'calendar' ? 'no-inspector' : ''}`}>
      <Sidebar />
      <MainContent />
      {activeView === 'calendar' && <Inspector />}
    </div>
  );
}
```

#### `stores/useAppStore.ts`
- Main Zustand store with all app state
- Navigation, data, selections, search
- Data loading actions
- No business logic (delegate to utils/hooks)

#### `stores/useCalendarStore.ts`
- Calendar-specific state (week navigation)
- Week change actions
- "Go to today" action

### Layout Components

#### `components/layout/Sidebar.tsx`
- Reads `activeView` from store
- Dispatches `setActiveView` on click
- Reads badge counts from store
- Renders 4 navigation blocks (Tasks, Calendar, Projects, Notes)

#### `components/layout/MainContent.tsx`
- Reads `activeView` from store
- Switches between view components
- Renders active view with `view-pane active` class

#### `components/layout/Inspector.tsx`
- Reads `selectedEvent`, `selectedNote` from store
- Calculates `linkedNotes`, `linkedTasks` from store data
- Renders event details, linked items, note preview
- Only shown for calendar view

### View Components

#### `components/calendar/CalendarView.tsx`
- Top-level calendar view
- Composes CalendarHeader + CalendarGrid
- Passes store data to children

#### `components/calendar/CalendarGrid.tsx`
- Renders grid with hours (0-23) and days
- Maps events to cells using `useCalendarUtils`
- Sticky day headers
- Scrollable content

#### `components/calendar/EventBlock.tsx`
- Single event block
- Receives event + style (height, top position)
- Dispatches `setSelectedEvent` on click
- Applies `getEventStyle` from utils

#### `components/tasks/TasksView.tsx`
- Reads `tasks`, `events`, `tasksSearch` from store
- Uses `useTaskFiltering` hook for filtered data
- Renders TaskSearch + TaskList
- Manages search input state dispatch

#### `components/tasks/TaskList.tsx`
- Receives filtered events with tasks + standalone tasks
- Renders multiple TaskGroup components
- Handles empty state

#### `components/tasks/TaskItem.tsx`
- Single task row
- Checkbox, text (cleaned), tags (event/project/deadline)
- Uses `cleanTaskDisplay` util function

#### `components/notes/NotesView.tsx`
- Reads `notes`, `notesSearch` from store
- Uses `useNoteFiltering` hook
- Renders NoteSearch + NotesGrid

#### `components/notes/NotesGrid.tsx`
- Grid layout of note tiles
- Maps filtered notes to NoteTile components

#### `components/notes/NoteTile.tsx`
- Single note tile
- Dispatches `setSelectedNote` on click
- Shows title + preview

### Hooks

#### `hooks/useGeraSync.ts`
```typescript
export function useGeraSync() {
  const { setEvents, setNotes, setTasks, setLoading } = useAppStore();
  
  const reloadData = useCallback(async () => {
    const weekRange = getWeekDateRange();
    const [ev, nt, tk] = await Promise.all([
      listEvents(weekRange),
      listNotes(),
      listFloatingTasks(),
    ]);
    setEvents(ev);
    setNotes(nt);
    setTasks(tk);
  }, [setEvents, setNotes, setTasks]);
  
  // Initial load
  useEffect(() => {
    reloadData().then(() => setLoading(false));
  }, [reloadData, setLoading]);
  
  // Listen to gera://fs-changed
  useEffect(() => {
    const unlisten = listen("gera://fs-changed", reloadData);
    return () => { unlisten.then(fn => fn()); };
  }, [reloadData]);
}
```

#### `hooks/useTaskFiltering.ts`
```typescript
export function useTaskFiltering(
  tasks: TaskEntity[],
  events: EventEntity[],
  search: string
) {
  const filterTask = useCallback((task: TaskEntity, search: string): boolean => {
    // Filter logic
  }, []);
  
  const standaloneTasks = useMemo(
    () => tasks.filter(t => t.event_ids.length === 0),
    [tasks]
  );
  
  const upcomingEventsWithTasks = useMemo(() => {
    return events
      .filter(ev => tasks.some(t => t.event_ids.includes(ev.id)))
      .sort((a, b) => new Date(a.from_).getTime() - new Date(b.from_).getTime());
  }, [events, tasks]);
  
  const filteredStandaloneTasks = useMemo(
    () => standaloneTasks.filter(t => filterTask(t, search)),
    [standaloneTasks, search, filterTask]
  );
  
  const filteredEventsWithTasks = useMemo(
    () => upcomingEventsWithTasks.filter(ev => {
      // Filter logic
    }),
    [upcomingEventsWithTasks, search]
  );
  
  return {
    filteredEventsWithTasks,
    filteredStandaloneTasks,
    getTasksForEvent: (id: string) => tasks.filter(t => t.event_ids.includes(id)),
  };
}
```

#### `hooks/useCalendarUtils.ts`
```typescript
export function useCalendarUtils() {
  const getWeekDates = useCallback(() => {
    const now = new Date();
    const monday = new Date(now);
    monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d;
    });
  }, []);
  
  const formatHour = useCallback((h: number) => {
    const suffix = h >= 12 ? "PM" : "AM";
    const display = h > 12 ? h - 12 : h === 0 ? 12 : h;
    return `${display} ${suffix}`;
  }, []);
  
  const getEventForCell = useCallback(
    (events: EventEntity[], hourIndex: number, dayIndex: number, weekDates: Date[]) => {
      // Filter events for specific cell
    },
    []
  );
  
  return { getWeekDates, formatHour, getEventForCell };
}
```

### Utils

#### `utils/taskFormatting.ts`
```typescript
export function cleanTaskDisplay(task: TaskEntity): string {
  let display = task.text;
  
  // Remove time references
  if (task.time_references) {
    for (const ref of task.time_references) {
      display = display.replace(
        `@${ref.modifier}[${ref.amount}${ref.unit}]:${ref.target_id}`,
        ""
      );
    }
  }
  
  // Remove event references
  if (task.event_ids && task.resolved_event_names) {
    for (const eid of task.event_ids) {
      const evName = task.resolved_event_names[eid];
      if (evName) {
        display = display.replace(`@${eid}`, "");
      }
    }
  }
  
  // Remove project references
  if (task.project_ids && task.resolved_project_names) {
    for (const pid of task.project_ids) {
      const projName = task.resolved_project_names[pid];
      if (projName) {
        display = display.replace(`#${pid}`, "");
      }
    }
  }
  
  // Remove datetime references
  display = display.replace(/@\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}/, "");
  
  return display.trim();
}

export interface TaskTags {
  eventTags: Array<{ id: string; name: string }>;
  projectTags: Array<{ id: string; name: string }>;
  hasDeadline: boolean;
}

export function getTaskTags(task: TaskEntity): TaskTags {
  const eventTags = Object.entries(task.resolved_event_names ?? {}).map(
    ([id, name]) => ({ id, name })
  );
  const projectTags = Object.entries(task.resolved_project_names ?? {}).map(
    ([id, name]) => ({ id, name })
  );
  const hasDeadline = !!task.deadline;
  
  return { eventTags, projectTags, hasDeadline };
}
```

#### `utils/eventPositioning.ts`
```typescript
export const HOUR_HEIGHT_PX = 56;

export interface EventStyle {
  height: string;
  top: string;
}

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
    
    // Height calculation
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
```

#### `utils/dateFormatting.ts`
```typescript
export function formatEventTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function formatEventDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

export function formatEventDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}
```

### Shared Components

#### `components/shared/Checkbox.tsx`
```typescript
interface CheckboxProps {
  checked: boolean;
  onChange?: () => void;
}

export function Checkbox({ checked, onChange }: CheckboxProps) {
  return (
    <div className={`checkbox ${checked ? 'checked' : ''}`} onClick={onChange}>
      {checked && <CheckIcon />}
    </div>
  );
}
```

#### `components/shared/Tag.tsx`
```typescript
interface TagProps {
  type: 'event' | 'project' | 'deadline';
  children: React.ReactNode;
}

export function Tag({ type, children }: TagProps) {
  return (
    <span className={`task-tag task-tag--${type}`}>
      {children}
    </span>
  );
}
```

#### `components/shared/SearchInput.tsx`
```typescript
interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({ value, onChange, placeholder, className }: SearchInputProps) {
  return (
    <input
      type="text"
      className={className}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
```

## Migration Strategy

### Phase 1: Setup Zustand & Extract Utilities (Day 1)

1. **Install Zustand**
   ```bash
   bun add zustand
   ```

2. **Create stores**
   - `src/stores/useAppStore.ts` - Main app state
   - `src/stores/useCalendarStore.ts` - Calendar state

3. **Create utils**
   - `src/utils/taskFormatting.ts` - Extract task display logic
   - `src/utils/eventPositioning.ts` - Extract event style calculation
   - `src/utils/dateFormatting.ts` - Extract date formatting

4. **Create types**
   - `src/types/index.ts` - Re-export api types

5. **Update App.tsx** to use Zustand store
   - Replace useState with store selectors
   - Test that everything still works

### Phase 2: Extract Hooks (Day 2)

1. **Create hooks**
   - `src/hooks/useGeraSync.ts` - Extract data loading + fs-changed
   - `src/hooks/useTaskFiltering.ts` - Extract task filtering logic
   - `src/hooks/useNoteFiltering.ts` - Extract note filtering logic
   - `src/hooks/useCalendarUtils.ts` - Extract calendar utilities

2. **Update App.tsx** to use these hooks
3. **Test that data sync and filtering work**

### Phase 3: Extract Icons & Shared Components (Day 3)

1. **Create icons**
   - `src/components/icons/Icons.tsx` - All SVG components

2. **Create shared components**
   - `src/components/shared/Checkbox.tsx`
   - `src/components/shared/Tag.tsx`
   - `src/components/shared/SearchInput.tsx`
   - `src/components/shared/EmptyState.tsx`

3. **Update App.tsx** to import from new locations

### Phase 4: Extract View Components (Days 4-5)

1. **Tasks view**
   - `src/components/tasks/TasksView.tsx`
   - `src/components/tasks/TaskList.tsx`
   - `src/components/tasks/TaskGroup.tsx`
   - `src/components/tasks/TaskItem.tsx`
   - `src/components/tasks/TaskSearch.tsx`

2. **Calendar view**
   - `src/components/calendar/CalendarView.tsx`
   - `src/components/calendar/CalendarGrid.tsx`
   - `src/components/calendar/CalendarHeader.tsx`
   - `src/components/calendar/EventBlock.tsx`
   - `src/components/calendar/DayHeader.tsx`

3. **Notes view**
   - `src/components/notes/NotesView.tsx`
   - `src/components/notes/NotesGrid.tsx`
   - `src/components/notes/NoteTile.tsx`
   - `src/components/notes/NoteSearch.tsx`

4. **Projects view**
   - `src/components/projects/ProjectsView.tsx`
   - `src/components/projects/ProjectsGrid.tsx`
   - `src/components/projects/ProjectTile.tsx`
   - `src/components/projects/ProjectSearch.tsx`

### Phase 5: Extract Layout Components (Day 6)

1. **Create layout components**
   - `src/components/layout/Sidebar.tsx`
   - `src/components/layout/MainContent.tsx`
   - `src/components/layout/Inspector.tsx`

2. **Slim down App.tsx** to just the shell (~50 lines)

3. **Test entire application**

### Phase 6: CSS Refactoring (Optional - Day 7)

1. **Split App.css**
   - `src/styles/variables.css` - Design tokens
   - `src/styles/layout.css` - Grid & layout
   - `src/styles/components.css` - Shared components
   - `src/styles/views.css` - View-specific styles

2. **Consider CSS modules** for component-specific styles (optional)

## Testing Checklist

After each phase, verify:

- [ ] Application starts without errors
- [ ] All views render correctly (Tasks, Calendar, Projects, Notes)
- [ ] Navigation between views works
- [ ] Search filters work in Tasks and Notes
- [ ] Calendar displays events correctly with proper sizing
- [ ] Clicking events updates inspector
- [ ] Task checkboxes display correctly
- [ ] Tags (event/project/deadline) display correctly
- [ ] Scrolling works independently for each pane
- [ ] Day headers stay sticky when scrolling calendar
- [ ] Inspector only shows for calendar view
- [ ] File system changes trigger data reload
- [ ] No TypeScript errors
- [ ] No console errors/warnings

## Benefits

✅ **Maintainability** - Each file <200 lines, single responsibility  
✅ **Testability** - Isolated components, hooks, utils are easy to test  
✅ **Reusability** - Shared components reduce duplication  
✅ **Readability** - Clear file organization, easy to navigate  
✅ **Collaboration** - Multiple devs can work on different areas  
✅ **Performance** - Zustand's fine-grained reactivity prevents unnecessary re-renders  
✅ **Scalability** - Easy to add new views, features, or state  
✅ **Type Safety** - Full TypeScript support with Zustand  

## Notes

- Keep the "Islands UI" design philosophy throughout
- Maintain the existing CSS classes and styling patterns
- Each component should be self-contained but use global styles
- Zustand store should be the single source of truth for all app state
- Extract business logic to utils/hooks, keep components presentational
- Use React.memo() strategically for expensive components (EventBlock, TaskItem)
