"""Tests for Gera Pydantic entity models."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from gera.entities import EventEntity, EventMetadata, NoteEntity, ProjectEntity, TaskEntity
from gera.entities.time_reference import TimeReference


# ── TaskEntity ────────────────────────────────────────────────────────────────


class TestTaskEntity:
    def test_minimal_construction(self):
        t = TaskEntity(
            text="Buy milk",
            completed=False,
            raw_line="- [ ] Buy milk",
            source_file="tasks.md",
            line_number=1,
        )
        assert t.text == "Buy milk"
        assert t.completed is False
        assert t.deadline is None
        assert t.event_ids == []
        assert t.project_ids == []
        assert t.time_references == []
        assert t.resolved_event_names == {}
        assert t.resolved_project_names == {}

    def test_completed_flag(self):
        t = TaskEntity(
            text="Done",
            completed=True,
            raw_line="- [x] Done",
            source_file="tasks.md",
            line_number=1,
        )
        assert t.completed is True

    def test_deadline_accepts_datetime(self):
        dt = datetime(2026, 3, 20, 9, 0)
        t = TaskEntity(
            text="Task",
            completed=False,
            raw_line="- [ ] Task",
            source_file="tasks.md",
            line_number=1,
            deadline=dt,
        )
        assert t.deadline == dt

    def test_event_and_project_ids(self):
        t = TaskEntity(
            text="Prep @standup #atlas",
            completed=False,
            raw_line="- [ ] Prep @standup #atlas",
            source_file="tasks.md",
            line_number=1,
            event_ids=["standup"],
            project_ids=["atlas"],
        )
        assert t.event_ids == ["standup"]
        assert t.project_ids == ["atlas"]

    def test_round_trip_serialization(self):
        t = TaskEntity(
            text="Round trip",
            completed=False,
            raw_line="- [ ] Round trip",
            source_file="tasks.md",
            line_number=5,
            deadline=datetime(2026, 4, 1, 10, 0),
            event_ids=["e1"],
            project_ids=["p1"],
        )
        restored = TaskEntity.model_validate(t.model_dump())
        assert restored == t


# ── TimeReference ─────────────────────────────────────────────────────────────


class TestTimeReference:
    def test_before_reference(self):
        ref = TimeReference(modifier="before", amount=2, unit="d", target_id="standup")
        assert ref.modifier == "before"
        assert ref.amount == 2
        assert ref.unit == "d"
        assert ref.target_id == "standup"

    def test_after_reference(self):
        ref = TimeReference(modifier="after", amount=1, unit="W", target_id="retro")
        assert ref.modifier == "after"
        assert ref.unit == "W"

    def test_round_trip(self):
        ref = TimeReference(modifier="before", amount=30, unit="m", target_id="standup-jan-20")
        assert TimeReference.model_validate(ref.model_dump()) == ref


# ── EventMetadata ─────────────────────────────────────────────────────────────


class TestEventMetadata:
    def test_defaults_to_empty_strings_and_none(self):
        m = EventMetadata()
        assert m.source_platform == "local"  # default is "local", not ""
        assert m.source_account == ""
        assert m.source_event_id == ""
        assert m.last_synced_at is None
        assert m.source_updated_at is None

    def test_explicit_values(self):
        m = EventMetadata(
            source_platform="google_calendar",
            source_account="user@example.com",
            source_event_id="gcal-123",
            etag="abc123",
        )
        assert m.source_platform == "google_calendar"
        assert m.etag == "abc123"

    def test_round_trip(self):
        m = EventMetadata(source_platform="google", etag="xyz")
        assert EventMetadata.model_validate(m.model_dump()) == m


# ── EventEntity ───────────────────────────────────────────────────────────────


class TestEventEntity:
    def test_construction(self):
        e = EventEntity(
            id="standup-1",
            source="local",
            from_=datetime(2026, 3, 14, 9, 0),
            to=datetime(2026, 3, 14, 9, 30),
            name="Standup",
            description="Daily sync",
            participants=["alice@example.com"],
            location="Zoom",
            metadata=EventMetadata(),
        )
        assert e.id == "standup-1"
        assert e.name == "Standup"
        assert e.participants == ["alice@example.com"]

    def test_empty_participants_and_location(self):
        e = EventEntity(
            id="e1",
            source="local",
            from_=datetime(2026, 1, 1, 10, 0),
            to=datetime(2026, 1, 1, 11, 0),
            name="Meeting",
            description="",
            participants=[],
            location="",
            metadata=EventMetadata(),
        )
        assert e.participants == []
        assert e.location == ""

    def test_round_trip(self):
        e = EventEntity(
            id="e1",
            source="google_calendar",
            from_=datetime(2026, 3, 14, 10, 0),
            to=datetime(2026, 3, 14, 11, 0),
            name="Retro",
            description="Sprint retro",
            participants=[],
            location="",
            metadata=EventMetadata(etag="abc"),
        )
        restored = EventEntity.model_validate(e.model_dump())
        assert restored.id == e.id
        assert restored.metadata.etag == "abc"


# ── NoteEntity ────────────────────────────────────────────────────────────────


class TestNoteEntity:
    def test_construction_with_defaults(self):
        n = NoteEntity(
            filename="meeting.md",
            title="Meeting Notes",
            body_preview="Discussion about Q2",
            raw_content="# Meeting Notes\n\nDiscussion about Q2",
        )
        assert n.filename == "meeting.md"
        assert n.event_ids == []
        assert n.project_ids == []

    def test_with_references(self):
        n = NoteEntity(
            filename="retro.md",
            title="Retro",
            body_preview="",
            raw_content="",
            event_ids=["retro-1"],
            project_ids=["atlas"],
        )
        assert n.event_ids == ["retro-1"]
        assert n.project_ids == ["atlas"]

    def test_round_trip(self):
        n = NoteEntity(
            filename="note.md",
            title="Note",
            body_preview="Preview",
            raw_content="Full content",
            event_ids=["e1"],
            project_ids=["p1"],
        )
        assert NoteEntity.model_validate(n.model_dump()) == n


# ── ProjectEntity ─────────────────────────────────────────────────────────────


class TestProjectEntity:
    def test_id_is_separate_from_filename(self):
        p = ProjectEntity(
            id="atlas",
            filename="atlas.md",
            title="Project Atlas",
            body_preview="Build the thing",
            raw_content="# Project Atlas\n\nBuild the thing",
        )
        assert p.id == "atlas"
        assert p.filename == "atlas.md"

    def test_round_trip(self):
        p = ProjectEntity(
            id="proj",
            filename="proj.md",
            title="Proj",
            body_preview="",
            raw_content="",
            event_ids=["e1"],
        )
        assert ProjectEntity.model_validate(p.model_dump()) == p
