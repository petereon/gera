import { useEffect, useCallback } from 'react';
import { listen } from '@tauri-apps/api/event';
import { listEvents, listNotes, listFloatingTasks, getWeekDateRange } from '../api';
import { useAppStore } from '../stores/useAppStore';

/**
 * Hook that manages initial data loading and filesystem change synchronization.
 * Listens to gera://fs-changed events and reloads data whenever files change.
 */
export function useGeraSync() {
  const setEvents = useAppStore((state) => state.setEvents);
  const setNotes = useAppStore((state) => state.setNotes);
  const setTasks = useAppStore((state) => state.setTasks);
  const setLoading = useAppStore((state) => state.setLoading);

  const reloadData = useCallback(async () => {
    try {
      const weekRange = getWeekDateRange();
      const [ev, nt, tk] = await Promise.all([
        listEvents(weekRange),
        listNotes(),
        listFloatingTasks(),
      ]);
      setEvents(ev);
      setNotes(nt);
      setTasks(tk);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  }, [setEvents, setNotes, setTasks]);

  // Initial load on mount
  useEffect(() => {
    reloadData().then(() => setLoading(false));
  }, [reloadData, setLoading]);

  // Listen to filesystem changes
  useEffect(() => {
    const unlisten = listen<{ changes: { type: string; path: string }[] }>(
      'gera://fs-changed',
      () => {
        reloadData();
      }
    );
    return () => {
      unlisten.then((fn) => fn());
    };
  }, [reloadData]);
}
