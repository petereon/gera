import { useMemo, useState, useEffect } from 'react';
import { NoteEntity, searchNotes } from '../api';
import { getNoteDedupeKey, deduplicate } from '../utils/deduplication';

/**
 * Hook that handles note filtering logic.
 * Filters floating notes (no event associations) by search query.
 * 
 * Hybrid search approach:
 * 1. First filters locally (instant, but limited to loaded data)
 * 2. If query is long enough and results are few, searches backend FTS5
 * 3. Merges results, deduplicating by filename:0:title_hash
 */
export function useNoteFiltering(notes: NoteEntity[], search: string) {
  const [backendResults, setBackendResults] = useState<NoteEntity[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Get notes without event associations
  const floatingNotes = useMemo(
    () => notes.filter((n) => n.event_ids.length === 0),
    [notes]
  );

  // Apply search filter (local filtering)
  const filteredFloatingNotes = useMemo(() => {
    if (!search) return floatingNotes;
    const searchLower = search.toLowerCase();
    return floatingNotes.filter(
      (n) =>
        n.title.toLowerCase().includes(searchLower) ||
        n.body_preview.toLowerCase().includes(searchLower)
    );
  }, [floatingNotes, search]);

  // Backend search: if local results are few and query is long enough, search backend
  useEffect(() => {
    if (search.length < 3) {
      setBackendResults([]);
      return;
    }

    if (filteredFloatingNotes.length < 5) {
      setIsSearching(true);
      const timer = setTimeout(async () => {
        try {
          const results = await searchNotes(search);
          // Filter to only floating notes (no event associations)
          const floatingBackendResults = results.filter((n) => n.event_ids.length === 0);
          setBackendResults(floatingBackendResults);
        } catch (error) {
          console.error('Backend note search failed:', error);
          setBackendResults([]);
        } finally {
          setIsSearching(false);
        }
      }, 300); // debounce 300ms

      return () => clearTimeout(timer);
    }
  }, [search, filteredFloatingNotes]);

  // Merge local and backend results, deduping by filename:0:title_hash
  const mergedFloatingNotes = useMemo(() => {
    if (backendResults.length === 0) return filteredFloatingNotes;
    
    // Get all notes (local + backend)
    const allNotes = [...filteredFloatingNotes, ...backendResults];

    // Deduplicate using filename + title hash
    return deduplicate(allNotes, getNoteDedupeKey);
  }, [filteredFloatingNotes, backendResults]);

  return {
    floatingNotes,
    filteredFloatingNotes: mergedFloatingNotes,
    isSearching,
  };
}
