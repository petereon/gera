"""Note service — domain operations for notes.

Delegates to Repository for all data access and file I/O.
"""

from __future__ import annotations

from gera.entities import NoteEntity
from gera.repository import Repository


def list_notes(repo: Repository) -> list[NoteEntity]:
    """Return all notes."""
    return repo.list_notes()


def get_note(repo: Repository, filename: str) -> NoteEntity | None:
    """Return a single note by filename, or None."""
    return repo.get_note(filename)


def search_notes(repo: Repository, query: str) -> list[NoteEntity]:
    """Full-text search across notes."""
    return repo.search_notes(query)


def create_note(
    repo: Repository,
    filename: str,
    content: str,
    event_ids: list[str] | None = None,
    project_ids: list[str] | None = None,
) -> NoteEntity:
    """Create a new note."""
    return repo.create_note(filename, content, event_ids=event_ids, project_ids=project_ids)


def update_note(repo: Repository, filename: str, content: str) -> NoteEntity:
    """Update an existing note."""
    return repo.update_note(filename, content)


def delete_note(repo: Repository, filename: str) -> None:
    """Delete a note by filename."""
    repo.delete_note(filename)
