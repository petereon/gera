import { useState } from 'react';
import { NoteEntity } from '../../types';
import { useAppStore } from '../../stores/useAppStore';
import { deleteNote } from '../../api';
import { TrashIcon } from '../icons/Icons';
import { ConfirmDialog } from '../shared/ConfirmDialog';

interface NoteTileProps {
  note: NoteEntity;
  onOpen?: () => void;
}

export function NoteTile({ note, onOpen }: NoteTileProps) {
  const setSelectedNote = useAppStore((state) => state.setSelectedNote);

  const handleClick = () => {
    if (onOpen) {
      onOpen();
    } else {
      setSelectedNote(note);
    }
  };
  const [confirming, setConfirming] = useState(false);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirming(true);
  };

  const handleConfirm = async () => {
    try {
      await deleteNote(note.filename);
    } catch (err) {
      console.error('Failed to delete note:', err);
    }
    setConfirming(false);
  };

  return (
    <>
      <div
        className="note-tile"
        onClick={handleClick}
      >
        <div className="note-tile-title">{note.title}</div>
        <div className="note-tile-preview">{note.body_preview}</div>
        <button
          className="note-tile-delete-btn"
          onClick={handleDeleteClick}
          aria-label="Delete note"
          title="Delete note"
        >
          <TrashIcon />
        </button>
      </div>
      {confirming && (
        <ConfirmDialog
          title="Delete note"
          message={`"${note.title}" will be permanently deleted.`}
          confirmLabel="Delete"
          onConfirm={handleConfirm}
          onCancel={() => setConfirming(false)}
        />
      )}
    </>
  );
}
