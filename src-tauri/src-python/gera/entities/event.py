"""Event entity model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from gera.entities.event_metadata import EventMetadata


class EventEntity(BaseModel):
    id: str
    source: str = "local"
    from_: datetime  # ISO-ish datetime string
    to: datetime
    name: str
    description: str = ""
    participants: list[str] = Field(default_factory=list)
    location: str = ""
    metadata: EventMetadata = Field(default_factory=EventMetadata)

    class Config:
        # allow `from` as alias since it's a Python keyword
        populate_by_name = True
