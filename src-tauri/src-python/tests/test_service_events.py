"""Tests for gera.service.events — thin delegation layer over Repository."""

from __future__ import annotations

from datetime import datetime


import gera.service.events as svc
from gera.entities import EventEntity, EventMetadata
from gera.repository import Repository


def _event(id: str = "e1", name: str = "Standup") -> EventEntity:
    return EventEntity(
        id=id,
        source="local",
        from_=datetime(2026, 3, 14, 9, 0),
        to=datetime(2026, 3, 14, 9, 30),
        name=name,
        description="",
        participants=[],
        location="",
        metadata=EventMetadata(),
    )


class TestServiceEvents:
    def test_list_events_empty(self, repo: Repository):
        assert svc.list_events(repo) == []

    def test_create_event_returns_entity(self, repo: Repository):
        evt = svc.create_event(repo, _event(id="e1", name="Retro"))
        assert evt.id == "e1"
        assert evt.name == "Retro"

    def test_created_event_appears_in_list(self, repo: Repository):
        svc.create_event(repo, _event(id="e1", name="Standup"))
        events = svc.list_events(repo)
        assert any(e.id == "e1" for e in events)

    def test_get_event_returns_entity(self, repo: Repository):
        svc.create_event(repo, _event(id="e1"))
        evt = svc.get_event(repo, "e1")
        assert evt is not None
        assert evt.id == "e1"

    def test_get_event_returns_none_for_missing(self, repo: Repository):
        assert svc.get_event(repo, "no-such") is None

    def test_update_event_changes_name(self, repo: Repository):
        svc.create_event(repo, _event(id="e1", name="Before"))
        svc.update_event(repo, _event(id="e1", name="After"))
        assert svc.get_event(repo, "e1").name == "After"

    def test_delete_event_removes_it(self, repo: Repository):
        svc.create_event(repo, _event(id="e1"))
        svc.delete_event(repo, "e1")
        assert svc.get_event(repo, "e1") is None

    def test_search_events_finds_match(self, repo: Repository):
        svc.create_event(repo, _event(id="e1", name="Daily Standup"))
        svc.create_event(repo, _event(id="e2", name="Sprint Retro"))
        results = svc.search_events(repo, "Standup")
        assert len(results) == 1
        assert results[0].id == "e1"

    def test_search_events_no_match(self, repo: Repository):
        svc.create_event(repo, _event(id="e1", name="Standup"))
        assert svc.search_events(repo, "zzznomatch") == []
