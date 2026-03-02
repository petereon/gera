import { useAppStore } from '../../stores/useAppStore';
import { useNoteFiltering } from '../../hooks/useNoteFiltering';
import { SearchInput } from '../shared/SearchInput';
import { NotesGrid } from './NotesGrid';

interface NotesViewProps {}

export function NotesView({}: NotesViewProps) {
  const notes = useAppStore((state) => state.notes);
  const notesSearch = useAppStore((state) => state.notesSearch);
  const setNotesSearch = useAppStore((state) => state.setNotesSearch);

  const { filteredFloatingNotes } = useNoteFiltering(notes, notesSearch);

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
      <NotesGrid notes={filteredFloatingNotes} />
    </div>
  );
}
