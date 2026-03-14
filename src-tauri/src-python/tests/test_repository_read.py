"""Tests for Repository read operations: list, search, pagination, filtering."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from gera.repository import Repository


# ── Helpers ───────────────────────────────────────────────────────────────────


def write_events(data_dir: Path, events: list[dict]) -> None:
    """Write a list of event dicts to events.yaml."""
    data_dir.joinpath("events.yaml").write_text(
        yaml.dump({"events": events}, default_flow_style=False),
        encoding="utf-8",
    )


def write_tasks(data_dir: Path, content: str) -> None:
    data_dir.joinpath("tasks.md").write_text(content, encoding="utf-8")


def write_note(data_dir: Path, filename: str, content: str) -> None:
    (data_dir / "notes" / filename).write_text(content, encoding="utf-8")


def write_project(data_dir: Path, filename: str, content: str) -> None:
    (data_dir / "projects" / filename).write_text(content, encoding="utf-8")


def _event_dict(
    id: str = "e1",
    name: str = "Standup",
    from_: str = "2026-03-14T09:00",
    to: str = "2026-03-14T09:30",
) -> dict:
    return {
        "id": id,
        "source": "local",
        "from": from_,
        "to": to,
        "name": name,
        "description": "",
        "participants": [],
        "location": "",
    }


# ── list_events ───────────────────────────────────────────────────────────────


class TestListEvents:
    def test_empty_returns_empty_list(self, repo: Repository):
        assert repo.list_events() == []

    def test_returns_loaded_events(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [_event_dict(id="e1", name="Standup")])
        repo.reload_events()
        events = repo.list_events()
        assert len(events) == 1
        assert events[0].id == "e1"
        assert events[0].name == "Standup"

    def test_multiple_events_all_returned(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [
            _event_dict(id="e1", name="Standup"),
            _event_dict(id="e2", name="Retro", from_="2026-03-14T14:00", to="2026-03-14T15:00"),
        ])
        repo.reload_events()
        assert len(repo.list_events()) == 2

    def test_malformed_events_yaml_returns_empty(self, data_dir: Path, repo: Repository):
        data_dir.joinpath("events.yaml").write_text("not: valid: yaml: {[\n", encoding="utf-8")
        repo.reload_events()
        assert repo.list_events() == []

    def test_events_sorted_by_start_time(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [
            _event_dict(id="later", name="Later", from_="2026-03-14T14:00", to="2026-03-14T15:00"),
            _event_dict(id="earlier", name="Earlier", from_="2026-03-14T09:00", to="2026-03-14T09:30"),
        ])
        repo.reload_events()
        events = repo.list_events()
        assert events[0].id == "earlier"
        assert events[1].id == "later"


# ── list_events_page (time-range filter) ─────────────────────────────────────


class TestListEventsPageFilter:
    def test_time_range_filter_excludes_outside(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [
            _event_dict(id="morning", from_="2026-03-14T09:00", to="2026-03-14T09:30"),
            _event_dict(id="evening", from_="2026-03-14T18:00", to="2026-03-14T19:00"),
        ])
        repo.reload_events()
        events, _ = repo.list_events_page(
            from_=datetime(2026, 3, 14, 8, 0),
            to=datetime(2026, 3, 14, 12, 0),
        )
        ids = [e.id for e in events]
        assert "morning" in ids
        assert "evening" not in ids

    def test_pagination_next_cursor_when_more(self, data_dir: Path, repo: Repository):
        evts = [_event_dict(id=f"e{i}", name=f"Event {i}", from_=f"2026-03-14T{9+i:02d}:00", to=f"2026-03-14T{9+i:02d}:30") for i in range(5)]
        write_events(data_dir, evts)
        repo.reload_events()
        page, cursor = repo.list_events_page(limit=3)
        assert len(page) == 3
        assert cursor is not None

    def test_pagination_no_cursor_on_last_page(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [_event_dict(id="only")])
        repo.reload_events()
        page, cursor = repo.list_events_page(limit=10)
        assert len(page) == 1
        assert cursor is None


# ── list_notes ────────────────────────────────────────────────────────────────


class TestListNotes:
    def test_empty_notes_dir_returns_empty(self, repo: Repository):
        assert repo.list_notes() == []

    def test_returns_note_from_file(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "standup.md", "# Daily Standup\n\nNotes here.")
        repo.reload_notes()
        notes = repo.list_notes()
        assert len(notes) == 1
        assert notes[0].filename == "standup.md"
        assert notes[0].title == "Daily Standup"

    def test_body_preview_populated(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "note.md", "# Title\n\nThis is the preview content.")
        repo.reload_notes()
        note = repo.list_notes()[0]
        assert note.body_preview != ""
        assert len(note.body_preview) <= 150

    def test_raw_content_stored(self, data_dir: Path, repo: Repository):
        content = "# Title\n\nFull content here."
        write_note(data_dir, "note.md", content)
        repo.reload_notes()
        assert repo.list_notes()[0].raw_content == content

    def test_event_ids_from_frontmatter(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "note.md", "---\nevent_ids:\n  - evt-1\n---\n# Note\n")
        repo.reload_notes()
        note = repo.list_notes()[0]
        assert "evt-1" in note.event_ids

    def test_filter_by_event_id(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "a.md", "---\nevent_ids:\n  - evt-1\n---\n# A\n")
        write_note(data_dir, "b.md", "# B\n\nNo event link.")
        repo.reload_notes()
        notes, _ = repo.list_notes_page(event_id="evt-1")
        assert len(notes) == 1
        assert notes[0].filename == "a.md"


# ── list_tasks / list_floating_tasks ─────────────────────────────────────────


class TestListTasks:
    def test_empty_tasks_md_returns_empty(self, repo: Repository):
        assert repo.list_tasks() == []

    def test_returns_task_from_file(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] Buy milk\n")
        repo.reload_tasks()
        tasks = repo.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].text == "Buy milk"
        assert tasks[0].completed is False

    def test_completed_task_loaded_correctly(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [x] Already done\n")
        repo.reload_tasks()
        assert repo.list_tasks()[0].completed is True

    def test_source_file_is_tasks_md(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] A task\n")
        repo.reload_tasks()
        assert repo.list_tasks()[0].source_file == "tasks.md"

    def test_task_with_event_ref_resolved_after_reload(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [_event_dict(id="standup", name="Daily Standup")])
        write_tasks(data_dir, "- [ ] Prep for @standup\n")
        repo.reload()
        task = repo.list_tasks()[0]
        assert "standup" in task.event_ids
        assert task.resolved_event_names.get("standup") == "Daily Standup"

    def test_unresolved_event_ref_does_not_crash(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] Task @ghost-event\n")
        repo.reload_tasks()
        task = repo.list_tasks()[0]
        assert "ghost-event" in task.event_ids
        assert task.resolved_event_names == {}


# ── list_projects ─────────────────────────────────────────────────────────────


class TestListProjects:
    def test_returns_project_from_file(self, data_dir: Path, repo: Repository):
        write_project(data_dir, "atlas.md", "# Project Atlas\n\nBuild the thing.")
        repo.reload_projects()
        projects = repo.list_projects()
        assert len(projects) == 1
        assert projects[0].id == "atlas"
        assert projects[0].title == "Project Atlas"


# ── search ────────────────────────────────────────────────────────────────────


class TestSearch:
    def test_search_tasks_finds_matching_text(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] Review slides\n- [ ] Buy groceries\n")
        repo.reload()
        results = repo.search_tasks("slides")
        assert len(results) == 1
        assert results[0].text == "Review slides"

    def test_search_tasks_no_match(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] Buy milk\n")
        repo.reload()
        assert repo.search_tasks("zzznomatch") == []

    def test_search_notes_by_title(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "retro.md", "# Sprint Retro\n\nWent well.")
        write_note(data_dir, "standup.md", "# Daily Standup\n\nQuick sync.")
        repo.reload()
        results = repo.search_notes("Retro")
        assert len(results) == 1
        assert results[0].filename == "retro.md"

    def test_search_notes_by_body(self, data_dir: Path, repo: Repository):
        write_note(data_dir, "note.md", "# Note\n\nAction items from the planning session.")
        repo.reload()
        results = repo.search_notes("planning")
        assert len(results) == 1

    def test_search_events_by_name(self, data_dir: Path, repo: Repository):
        write_events(data_dir, [
            _event_dict(id="standup", name="Daily Standup"),
            _event_dict(id="retro", name="Sprint Retro", from_="2026-03-14T14:00", to="2026-03-14T15:00"),
        ])
        repo.reload_events()
        results = repo.search_events("Standup")
        assert len(results) == 1
        assert results[0].id == "standup"

    def test_search_projects_by_title(self, data_dir: Path, repo: Repository):
        write_project(data_dir, "atlas.md", "# Atlas\n\nBig project.")
        write_project(data_dir, "hermes.md", "# Hermes\n\nSmall project.")
        repo.reload()
        results = repo.search_projects("Atlas")
        assert len(results) == 1
        assert results[0].id == "atlas"

    def test_search_is_case_insensitive(self, data_dir: Path, repo: Repository):
        write_tasks(data_dir, "- [ ] Review slides\n")
        repo.reload()
        assert len(repo.search_tasks("REVIEW")) >= 1

    def test_get_note_returns_none_for_missing(self, repo: Repository):
        assert repo.get_note("nonexistent.md") is None

    def test_get_event_returns_none_for_missing(self, repo: Repository):
        assert repo.get_event("no-such-id") is None
