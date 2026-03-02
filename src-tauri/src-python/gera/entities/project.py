"""Project entity model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectEntity(BaseModel):
    id: str
    """Project ID = filename without extension."""
    filename: str
    title: str
    body_preview: str
    event_ids: list[str] = Field(default_factory=list)
    raw_content: str
