"""Note entity model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NoteEntity(BaseModel):
    filename: str
    title: str
    body_preview: str
    """First ~100 chars of plain body text."""
    event_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    raw_content: str
    """Full file content (for rendering / editing)."""
