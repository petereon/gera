"""Event metadata for source tracking and deduplication."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventMetadata(BaseModel):
    """Source tracking metadata for deduplication across fetches."""

    source_platform: str = "local"  # "local" | "google_calendar" | ...
    source_account: str = ""  # e.g. "user@gmail.com"
    source_event_id: str = ""  # platform-native ID (Google: event.id)
    source_calendar_id: str = ""  # e.g. "primary", "work@group.calendar.google.com"
    etag: str = ""  # Google Calendar ETag for change detection
    last_synced_at: Optional[datetime] = None  # when we last pulled this event
    recurring_event_id: str = ""  # Google recurring event master ID
    source_updated_at: Optional[datetime] = None  # upstream updated timestamp (for conflict detection)

    class Config:
        populate_by_name = True
