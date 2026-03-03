import { useEffect, useState } from 'react';
import { useAppStore } from '../../stores/useAppStore';
import { useNoteFiltering } from '../../hooks/useNoteFiltering';
import { getNoteContent } from '../../api';
import { SearchInput } from '../shared/SearchInput';
import { NotesGrid } from './NotesGrid';
import { NoteEditor } from '../../editor/NoteEditor';
import { CloseIcon } from '../icons/Icons';
import { parseFrontmatter } from '../../utils/frontmatter';

interface NotesViewProps {}

export function NotesView({}: NotesViewProps) {
  const notes = useAppStore((state) => state.notes);
  const notesSearch = useAppStore((state) => state.notesSearch);
  const setNotesSearch = useAppStore((state) => state.setNotesSearch);
  const selectedNote = useAppStore((state) => state.selectedNote);
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);

  const { filteredNotes } = useNoteFiltering(notes, notesSearch);

  // State for the editor — null means "not yet loaded for this note"
  const [noteContent, setNoteContent] = useState<string | null>(null);
  const [eventIds, setEventIds] = useState<string[]>([]);
  const [projectIds, setProjectIds] = useState<string[]>([]);
  const [isLoadingNote, setIsLoadingNote] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load note content when selectedNote changes
  useEffect(() => {
    if (!selectedNote) {
      setNoteContent(null);
      setLoadError(null);
      return;
    }

    // Reset immediately so NoteEditor doesn't mount with stale content
    setNoteContent(null);
    setIsLoadingNote(true);
    setLoadError(null);

    getNoteContent(selectedNote.filename)
      .then((result) => {
        try {
          // Parse frontmatter and strip it from editor content
          const { metadata, body } = parseFrontmatter(result.raw_content);
          setNoteContent(body);
          setEventIds(metadata.event_ids || []);
          setProjectIds(metadata.project_ids || []);
        } catch (parseError) {
          console.error('Frontmatter parsing error:', parseError);
          // Fall back to showing raw content if parsing fails
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

  // If a note is selected, show the editor
  if (selectedNote) {
    return (
      <div className="notes-view notes-view--editor-mode">
        <div className="note-editor-header">
          <h2 className="note-title">{selectedNote.title}</h2>
          <button 
            className="close-btn" 
            onClick={() => setSelectedNote(null)} 
            aria-label="Close note"
          >
            <CloseIcon />
          </button>
        </div>

        {isLoadingNote || noteContent === null ? (
          <div className="note-loading">Loading...</div>
        ) : loadError ? (
          <div className="note-error">{loadError}</div>
        ) : (
          <>
            {/* Frontmatter metadata chips */}
            {(eventIds.length > 0 || projectIds.length > 0) && (
              <div className="note-metadata-chips">
                {eventIds.map((eventId) => (
                  <span key={eventId} className="metadata-chip metadata-chip--event">
                    @{eventId}
                  </span>
                ))}
                {projectIds.map((projectId) => (
                  <span key={projectId} className="metadata-chip metadata-chip--project">
                    #{projectId}
                  </span>
                ))}
              </div>
            )}
            <div className="note-editor-container">
              {/* key={filename} forces a clean remount whenever a different note
                  is opened, so stale Lexical editor state never bleeds across. */}
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
        <div className="section-label">NOTES</div>
        <SearchInput
          value={notesSearch}
          onChange={setNotesSearch}
          placeholder="Search by event, project, time-range..."
          className="notes-search"
        />
      </div>
      <div className="notes-content">
        <NotesGrid notes={filteredNotes} />
      </div>
    </div>
  );
}
