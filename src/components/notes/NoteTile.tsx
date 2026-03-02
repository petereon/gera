import { NoteEntity } from '../../types';
import { useAppStore } from '../../stores/useAppStore';

interface NoteTileProps {
  note: NoteEntity;
}

export function NoteTile({ note }: NoteTileProps) {
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);

  return (
    <div
      className="note-tile"
      onClick={() => setSelectedNote(note)}
    >
      <div className="note-tile-title">{note.title}</div>
      <div className="note-tile-preview">{note.body_preview}</div>
    </div>
  );
}
