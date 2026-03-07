import { useMemo, useCallback, useState, useEffect } from 'react';
import { EventEntity, TaskEntity, searchTasks } from '../api';
import { getTaskDedupeKey, deduplicate } from '../utils/deduplication';

/**
 * Hook that handles task filtering and grouping logic.
 * Separates standalone tasks from event-linked tasks and filters both by search query.
 * 
 * Hybrid search approach:
 * 1. First filters locally (instant, but limited to loaded data)
 * 2. If query is long enough and results are few, searches backend FTS5
 * 3. Merges results, deduplicating by source_file:line_number:text_hash
 */
export function useTaskFiltering(
  tasks: TaskEntity[],
  events: EventEntity[],
  search: string
) {
  const [backendResults, setBackendResults] = useState<TaskEntity[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Helper function to filter individual tasks
  const filterTask = useCallback((task: TaskEntity, searchText: string): boolean => {
    if (!searchText) return true;
    const searchLower = searchText.toLowerCase();

    // Search in task text
    if (task.text.toLowerCase().includes(searchLower)) return true;

    // Search in resolved event names
    if (task.resolved_event_names) {
      for (const name of Object.values(task.resolved_event_names)) {
        if ((name as string).toLowerCase().includes(searchLower)) return true;
      }
    }

    // Search in resolved project names
    if (task.resolved_project_names) {
      for (const name of Object.values(task.resolved_project_names)) {
        if ((name as string).toLowerCase().includes(searchLower)) return true;
      }
    }

    return false;
  }, []);

  // Get map of task IDs to tasks for event linking
  const tasksByEventId = useMemo(() => {
    const map = new Map<string, TaskEntity[]>();
    events.forEach((event) => {
      map.set(event.id, tasks.filter((t) => t.event_ids.includes(event.id)));
    });
    return map;
  }, [tasks, events]);

  // Tasks with no event associations (shown in "Other Tasks" group)
  const otherTasks = useMemo(
    () => tasks.filter((t) => t.event_ids.length === 0),
    [tasks]
  );

  // Events that have tasks, sorted by time
  const upcomingEventsWithTasks = useMemo(
    () =>
      events
        .filter((ev) => (tasksByEventId.get(ev.id)?.length ?? 0) > 0)
        .sort((a, b) => new Date(a.from_).getTime() - new Date(b.from_).getTime()),
    [events, tasksByEventId]
  );

  // Apply search filter to other tasks (local filtering)
  const filteredOtherTasks = useMemo(
    () => otherTasks.filter((t) => filterTask(t, search)),
    [otherTasks, search, filterTask]
  );

  // Apply search filter to events with tasks (local filtering)
  const filteredEventsWithTasks = useMemo(() => {
    if (!search) return upcomingEventsWithTasks;
    const searchLower = search.toLowerCase();
    return upcomingEventsWithTasks.filter((ev) => {
      // Include event if name matches
      if (ev.name.toLowerCase().includes(searchLower)) return true;
      // Include event if any task matches
      const eventTasks = tasksByEventId.get(ev.id) ?? [];
      return eventTasks.some((t) => filterTask(t, search));
    });
  }, [upcomingEventsWithTasks, search, filterTask, tasksByEventId]);

  // Backend search: if local results are few and query is long enough, search backend
  useEffect(() => {
    if (search.length < 3) {
      setBackendResults([]);
      return;
    }

    const localResultCount = filteredOtherTasks.length + filteredEventsWithTasks.length;
    
    // Only search backend if we have few local results
    if (localResultCount < 5) {
      setIsSearching(true);
      const timer = setTimeout(async () => {
        try {
          const results = await searchTasks(search);
          setBackendResults(results);
        } catch (error) {
          console.error('Backend task search failed:', error);
          setBackendResults([]);
        } finally {
          setIsSearching(false);
        }
      }, 300); // debounce 300ms

      return () => clearTimeout(timer);
    }
  }, [search, filteredOtherTasks, filteredEventsWithTasks]);

  // Merge local and backend results, deduping by source_file:line_number:text_hash
  const mergedOtherTasks = useMemo(() => {
    if (backendResults.length === 0) return filteredOtherTasks;
    const allTasks = [...filteredOtherTasks, ...backendResults.filter((t) => t.event_ids.length === 0)];
    return deduplicate(allTasks, getTaskDedupeKey);
  }, [filteredOtherTasks, backendResults]);

  // Timeline: all tasks sorted by earliest associated event date; unscheduled last
  const timelineTasks = useMemo(() => {
    const allFiltered = tasks.filter((t) => filterTask(t, search));
    const merged = backendResults.length > 0
      ? deduplicate([...allFiltered, ...backendResults], getTaskDedupeKey)
      : allFiltered;

    const getEarliestMs = (task: TaskEntity): number => {
      if (!task.event_ids.length) return Infinity;
      const dates = task.event_ids
        .map((id) => events.find((e) => e.id === id)?.from_)
        .filter((d): d is string => !!d)
        .map((d) => new Date(d).getTime());
      return dates.length ? Math.min(...dates) : Infinity;
    };

    return [...merged].sort((a, b) => getEarliestMs(a) - getEarliestMs(b));
  }, [tasks, events, search, filterTask, backendResults]);

  // Helper to get tasks for a specific event
  const getTasksForEvent = useCallback(
    (eventId: string) => tasksByEventId.get(eventId) ?? [],
    [tasksByEventId]
  );

  return {
    filteredEventsWithTasks,
    filteredOtherTasks: mergedOtherTasks,
    timelineTasks,
    getTasksForEvent,
    isSearching,
  };
}
