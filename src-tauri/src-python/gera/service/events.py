"""Event service — domain operations for events.

Delegates to Repository for all data access and file I/O.
"""

from __future__ import annotations

from gera.entities import EventEntity
from gera.repository import Repository


def list_events(repo: Repository) -> list[EventEntity]:
    """Return all events."""
    return repo.list_events()


def get_event(repo: Repository, event_id: str) -> EventEntity | None:
    """Return a single event by ID, or None."""
    return repo.get_event(event_id)


def search_events(repo: Repository, query: str) -> list[EventEntity]:
    """Full-text search across events."""
    return repo.search_events(query)


def create_event(repo: Repository, event: EventEntity) -> EventEntity:
    """Create a new event."""
    return repo.create_event(event)


def update_event(repo: Repository, event: EventEntity) -> EventEntity:
    """Update an existing event."""
    return repo.update_event(event)


def delete_event(repo: Repository, event_id: str) -> None:
    """Delete an event by ID."""
    repo.delete_event(event_id)
