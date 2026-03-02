"""Task entity model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from gera.entities.time_reference import TimeReference


class TaskEntity(BaseModel):
    text: str
    completed: bool
    raw_line: str
    """Original markdown line (for write-back)."""
    source_file: str
    """Relative path to the file containing this task."""
    line_number: int
    deadline: datetime | None = None
    event_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    time_references: list[TimeReference] = Field(default_factory=list)
    """Parsed @before/@after offset references (for deadline resolution)."""

    # --- Resolved fields (populated by service layer, not parser) ---
    resolved_event_names: dict[str, str] = Field(default_factory=dict)
    """event_id → display name, filled by resolve_tasks()."""
    resolved_project_names: dict[str, str] = Field(default_factory=dict)
    """project_id → display title, filled by resolve_tasks()."""
