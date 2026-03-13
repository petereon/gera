import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../stores/useAppStore';
import { useNoteFiltering } from '../../hooks/useNoteFiltering';
import { getNoteContent, createNote, updateNoteContent } from '../../api';
import { SearchInput } from '../shared/SearchInput';
import { NotesGrid } from './NotesGrid';
import { NoteEditor } from '../../editor/NoteEditor';
import { PlusIcon } from '../icons/Icons';
import { parseFrontmatter } from '../../utils/frontmatter';

interface NotesViewProps {}

export function NotesView({}: NotesViewProps) {
  const events = useAppStore((state) => state.events);
  const notes = useAppStore((state) => state.notes);
  const notesSearch = useAppStore((state) => state.notesSearch);
  const setNotesSearch = useAppStore((state) => state.setNotesSearch);
  const selectedNote = useAppStore((state) => state.selectedNote);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);
  const returnView = useAppStore((state) => state.returnView);
  const setReturnView = useAppStore((state) => state.setReturnView);
  const pendingCreate = useAppStore((state) => state.pendingCreate);
  const setPendingCreate = useAppStore((state) => state.setPendingCreate);
  const searchFocusTrigger = useAppStore((state) => state.searchFocusTrigger);
  const navigate = useNavigate();

  const { filteredNotes } = useNoteFiltering(notes, notesSearch);

  // State for the editor — null means "not yet loaded for this note"
  const [noteContent, setNoteContent] = useState<string | null>(null);
  const [eventIds, setEventIds] = useState<string[]>([]);
  const [projectIds, setProjectIds] = useState<string[]>([]);
  const [isLoadingNote, setIsLoadingNote] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Event picker state
  const [showEventPicker, setShowEventPicker] = useState(false);
  const [eventSearch, setEventSearch] = useState('');
  const pickerRef = useRef<HTMLDivElement>(null);
  const pickerSearchRef = useRef<HTMLInputElement>(null);

  // Escape closes the note editor and returns to grid
  useEffect(() => {
    if (!selectedNote) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setSelectedNote(null);
        if (returnView) { setReturnView(null); navigate(returnView); }
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [selectedNote, returnView, setSelectedNote, setReturnView, navigate]);

  // Focus search input when event picker opens
  useEffect(() => {
    if (showEventPicker) pickerSearchRef.current?.focus();
  }, [showEventPicker]);

  // Close picker when clicking outside
  useEffect(() => {
    if (!showEventPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowEventPicker(false);
        setEventSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showEventPicker]);

  // Load note content when selectedNote changes
  useEffect(() => {
    if (!selectedNote) {
      setNoteContent(null);
      setLoadError(null);
      return;
    }

    setNoteContent(null);
    setIsLoadingNote(true);
    setLoadError(null);

    getNoteContent(selectedNote.filename)
      .then((result) => {
        try {
          const { metadata, body } = parseFrontmatter(result.raw_content);
          setNoteContent(body);
          setEventIds(metadata.event_ids || []);
          setProjectIds(metadata.project_ids || []);
        } catch (parseError) {
          console.error('Frontmatter parsing error:', parseError);
          setNoteContent(result.raw_content);
          setEventIds([]);
          setProjectIds([]);
        }
      })
      .catch((err) => {
        console.error('Failed to load note:', err);
        setLoadError('Failed to load note');
      })
      .finally(() => {
        setIsLoadingNote(false);
      });
  }, [selectedNote]);

  // Save metadata — fetch latest body from disk rather than relying on stale state
  const handleMetadataChange = async (newEventIds: string[], newProjectIds: string[]) => {
    if (!selectedNote) return;
    try {
      const result = await getNoteContent(selectedNote.filename);
      const { body } = parseFrontmatter(result.raw_content);

      const lines: string[] = ['---'];
      if (newEventIds.length > 0) {
        lines.push('event_ids:');
        newEventIds.forEach((id) => lines.push(`  - ${id}`));
      }
      if (newProjectIds.length > 0) {
        lines.push('project_ids:');
        newProjectIds.forEach((id) => lines.push(`  - ${id}`));
      }
      const frontmatter = (newEventIds.length > 0 || newProjectIds.length > 0)
        ? lines.join('\n') + '\n---\n\n'
        : '';

      await updateNoteContent(selectedNote.filename, frontmatter + body);
    } catch (err) {
      console.error('Failed to update note metadata:', err);
    }
  };

  const removeEventId = (id: string) => {
    const next = eventIds.filter((e) => e !== id);
    setEventIds(next);
    handleMetadataChange(next, projectIds);
  };

  const addEventId = (id: string) => {
    if (eventIds.includes(id)) return;
    const next = [...eventIds, id];
    setEventIds(next);
    handleMetadataChange(next, projectIds);
    setShowEventPicker(false);
    setEventSearch('');
  };

  const handleCreateNote = async () => {
    try {
      const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const filename = `note-${ts}`;
      const note = await createNote(filename, '');
      setSelectedNote(note);
    } catch (error) {
      console.error('Failed to create note:', error);
    }
  };

  useEffect(() => {
    if (pendingCreate === 'note') {
      setPendingCreate(null);
      handleCreateNote();
    }
  // handleCreateNote is stable — intentionally omitted from deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCreate, setPendingCreate]);

  // Events not yet linked, filtered by search
  const availableEvents = events.filter(
    (e) => !eventIds.includes(e.id) &&
      (eventSearch === '' || e.name.toLowerCase().includes(eventSearch.toLowerCase()))
  );

  // If a note is selected, show the editor
  if (selectedNote) {
    return (
      <div className="notes-view notes-view--editor-mode">
        {isLoadingNote || noteContent === null ? (
          <div className="note-loading">Loading...</div>
        ) : loadError ? (
          <div className="note-error">{loadError}</div>
        ) : (
          <>
            {/* Header row — mirrors the notes grid section-header-row */}
            <div className="note-editor-topbar">
              <div className="section-label">NOTE</div>
              <button
                className="icon-btn note-close-btn"
                onClick={() => {
                  setSelectedNote(null);
                  if (returnView) {
                    setReturnView(null);
                    navigate(returnView);
                  }
                }}
                aria-label="Close note"
                title="Close note"
              >
                ✕
              </button>
            </div>
            {/* Frontmatter metadata chips */}
            <div className="note-metadata-chips">
              {eventIds.map((id) => {
                const event = events.find((e) => e.id === id);
                return (
                  <span key={id} className="metadata-chip metadata-chip--event">
                    @{event?.name ?? id}
                    <button
                      className="metadata-chip-remove"
                      onClick={() => removeEventId(id)}
                      aria-label={`Remove event ${id}`}
                      title="Remove"
                    >
                      ×
                    </button>
                  </span>
                );
              })}
              {projectIds.map((id) => (
                <span key={id} className="metadata-chip metadata-chip--project">
                  #{id}
                </span>
              ))}
              {/* Add event picker */}
              <div className="metadata-add-wrapper" ref={pickerRef}>
                <button
                  className="metadata-chip metadata-chip--add"
                  onClick={() => { setShowEventPicker((v) => !v); setEventSearch(''); }}
                  title="Link event"
                >
                  + Event
                </button>
                {showEventPicker && (
                  <div className="metadata-event-picker">
                    <input
                      ref={pickerSearchRef}
                      className="metadata-picker-search"
                      placeholder="Search events…"
                      value={eventSearch}
                      onChange={(e) => setEventSearch(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'ArrowDown') {
                          e.preventDefault();
                          (pickerRef.current?.querySelector<HTMLButtonElement>('.metadata-picker-item'))?.focus();
                        } else if (e.key === 'Escape') {
                          e.stopPropagation();
                          setShowEventPicker(false);
                          setEventSearch('');
                        }
                      }}
                    />
                    <div className="metadata-picker-list">
                      {availableEvents.length === 0 ? (
                        <div className="metadata-picker-empty">No events found</div>
                      ) : (
                        availableEvents.map((e) => (
                          <button
                            key={e.id}
                            className="metadata-picker-item"
                            onClick={() => addEventId(e.id)}
                            onKeyDown={(ev) => {
                              if (ev.key === 'ArrowDown') {
                                ev.preventDefault();
                                ev.stopPropagation();
                                (ev.currentTarget.nextElementSibling as HTMLButtonElement | null)?.focus();
                              } else if (ev.key === 'ArrowUp') {
                                ev.preventDefault();
                                ev.stopPropagation();
                                const prev = ev.currentTarget.previousElementSibling as HTMLButtonElement | null;
                                if (prev) prev.focus();
                                else pickerRef.current?.querySelector<HTMLInputElement>('.metadata-picker-search')?.focus();
                              } else if (ev.key === 'Escape') {
                                ev.stopPropagation();
                                setShowEventPicker(false);
                                setEventSearch('');
                              }
                            }}
                          >
                            {e.name}
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="note-editor-container">
              <NoteEditor
                key={selectedNote.filename}
                filename={selectedNote.filename}
                content={noteContent}
                eventIds={eventIds}
                projectIds={projectIds}
                autoSave={true}
                autoSaveDelay={1000}
              />
            </div>
          </>
        )}
      </div>
    );
  }

  // Otherwise show the notes grid
  return (
    <div className="notes-view">
      <div className="notes-header">
        <div className="section-header-row">
          <div className="section-label">NOTES</div>
          <button
            className="icon-btn icon-btn--accent"
            onClick={handleCreateNote}
            aria-label="New note"
            title="New note"
          >
            <PlusIcon />
          </button>
        </div>
        <SearchInput
          value={notesSearch}
          onChange={setNotesSearch}
          placeholder="Search by event, project, time-range..."
          className="notes-search"
          focusTrigger={searchFocusTrigger}
        />
      </div>
      <div className="notes-content">
        <NotesGrid notes={filteredNotes} />
      </div>
    </div>
  );
}
