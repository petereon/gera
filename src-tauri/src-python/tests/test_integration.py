"""Integration tests — end-to-end flows across all layers using a real Repository."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from gera.entities import EventEntity, EventMetadata
from gera.repository import Repository
import gera.service.events as event_svc
import gera.service.notes as note_svc
import gera.service.tasks as task_svc


def _event(id: str, name: str) -> EventEntity:
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


# ── Task lifecycle ─────────────────────────────────────────────────────────────


class TestTaskLifecycle:
    def test_full_create_list_toggle_delete_cycle(self, repo: Repository):
        # 1. Empty at start
        assert task_svc.list_tasks(repo) == []

        # 2. Create
        task_svc.create_task(repo, "Buy oat milk")
        tasks = task_svc.list_tasks(repo)
        assert len(tasks) == 1
        t = tasks[0]
        assert t.text == "Buy oat milk"
        assert t.completed is False

        # 3. Toggle → completed
        task_svc.toggle_task(repo, t.source_file, t.line_number)
        tasks = task_svc.list_tasks(repo)
        assert tasks[0].completed is True

        # 4. Toggle back → incomplete
        task_svc.toggle_task(repo, t.source_file, t.line_number)
        assert task_svc.list_tasks(repo)[0].completed is False

        # 5. Delete
        task_svc.delete_task(repo, t.source_file, t.line_number)
        assert task_svc.list_tasks(repo) == []

    def test_multiple_tasks_independent(self, repo: Repository):
        task_svc.create_task(repo, "First")
        task_svc.create_task(repo, "Second")
        task_svc.create_task(repo, "Third")
        tasks = task_svc.list_tasks(repo)
        assert len(tasks) == 3

        # Toggle only the second
        second = next(t for t in tasks if t.text == "Second")
        task_svc.toggle_task(repo, second.source_file, second.line_number)

        refreshed = task_svc.list_tasks(repo)
        completed = {t.text for t in refreshed if t.completed}
        incomplete = {t.text for t in refreshed if not t.completed}
        assert completed == {"Second"}
        assert incomplete == {"First", "Third"}

    def test_task_text_updated_in_place(self, repo: Repository):
        task_svc.create_task(repo, "Old text")
        t = task_svc.list_tasks(repo)[0]
        task_svc.update_task(repo, t.source_file, t.line_number, "New text")
        tasks = task_svc.list_tasks(repo)
        assert tasks[0].text == "New text"
        assert len(tasks) == 1


# ── Note with cross-references ────────────────────────────────────────────────


class TestNoteWithCrossReferences:
    def test_note_linked_to_event_resolves_name(self, repo: Repository):
        # Create an event first
        event_svc.create_event(repo, _event("retro-1", "Sprint Retro"))

        # Create a note referencing that event
        note_svc.create_note(
            repo, "retro-notes.md", "# Retro Notes\n\nKey outcomes.", event_ids=["retro-1"]
        )

        notes = note_svc.list_notes(repo)
        assert len(notes) == 1
        assert "retro-1" in notes[0].event_ids

    def test_note_searchable_after_create(self, repo: Repository):
        note_svc.create_note(repo, "retro.md", "# Sprint Retro\n\nDecisions made here.")
        results = note_svc.search_notes(repo, "Decisions")
        assert len(results) == 1
        assert results[0].filename == "retro.md"

    def test_delete_note_removed_from_search(self, repo: Repository):
        note_svc.create_note(repo, "retro.md", "# Sprint Retro\n\nContent.")
        note_svc.delete_note(repo, "retro.md")
        assert note_svc.search_notes(repo, "Retro") == []

    def test_update_note_reflected_in_search(self, repo: Repository):
        note_svc.create_note(repo, "note.md", "# Note\n\nOld content.")
        note_svc.update_note(repo, "note.md", "# Note\n\nBrand new content.")
        assert note_svc.search_notes(repo, "Brand new") != []
        assert note_svc.search_notes(repo, "Old content") == []


# ── FTS across explicit reload ────────────────────────────────────────────────


class TestFTSAcrossReload:
    def test_fts_works_after_fresh_repository(self, data_dir: Path):
        # Write three events directly to disk
        events_yaml = {
            "events": [
                {
                    "id": "standup",
                    "source": "local",
                    "from": "2026-03-14T09:00",
                    "to": "2026-03-14T09:30",
                    "name": "Daily Standup",
                    "description": "Quick sync",
                    "participants": [],
                    "location": "",
                },
                {
                    "id": "retro",
                    "source": "local",
                    "from": "2026-03-14T14:00",
                    "to": "2026-03-14T15:00",
                    "name": "Sprint Retro",
                    "description": "Review sprint",
                    "participants": [],
                    "location": "",
                },
            ]
        }
        (data_dir / "events.yaml").write_text(
            yaml.dump(events_yaml, default_flow_style=False), encoding="utf-8"
        )

        # Create a fresh repository from the same data_dir
        repo2 = Repository(data_dir)
        repo2.reload()
        try:
            results = repo2.search_events("Standup")
            assert len(results) == 1
            assert results[0].id == "standup"

            no_results = repo2.search_events("zzznomatch")
            assert no_results == []
        finally:
            repo2.close()

    def test_task_fts_after_file_written_and_reloaded(self, data_dir: Path):
        (data_dir / "tasks.md").write_text(
            "- [ ] Review the architecture doc\n- [ ] Buy coffee\n",
            encoding="utf-8",
        )
        repo2 = Repository(data_dir)
        repo2.reload()
        try:
            results = repo2.search_tasks("architecture")
            assert len(results) == 1
            assert "architecture" in results[0].text
        finally:
            repo2.close()


# ── Cross-entity reference resolution ────────────────────────────────────────


class TestCrossEntityResolution:
    def test_task_with_event_ref_resolved(self, data_dir: Path, repo: Repository):
        # Create event then write a task that references it
        event_svc.create_event(repo, _event("standup", "Daily Standup"))
        task_svc.create_task(repo, "Prep notes for @standup")

        tasks = task_svc.list_tasks(repo)
        task = next(t for t in tasks if "standup" in t.event_ids)
        assert task.resolved_event_names.get("standup") == "Daily Standup"

    def test_task_deadline_computed_from_before_ref(self, data_dir: Path, repo: Repository):
        event_svc.create_event(
            repo,
            EventEntity(
                id="sprint-kickoff",
                source="local",
                from_=datetime(2026, 3, 20, 9, 0),
                to=datetime(2026, 3, 20, 10, 0),
                name="Sprint Kickoff",
                description="",
                participants=[],
                location="",
                metadata=EventMetadata(),
            ),
        )
        # Write task directly so the Gera syntax is parsed by reload
        (data_dir / "tasks.md").write_text(
            "- [ ] Prepare slides @before[1d]:sprint-kickoff\n", encoding="utf-8"
        )
        repo.reload()

        tasks = task_svc.list_tasks(repo)
        assert len(tasks) == 1
        t = tasks[0]
        # Deadline should be 1 day before the event start: 2026-03-19T09:00
        assert t.deadline is not None
        assert t.deadline.day == 19
        assert t.deadline.month == 3

    def test_note_task_inherits_note_event_ids(self, data_dir: Path, repo: Repository):
        event_svc.create_event(repo, _event("retro-1", "Retro"))
        # Note with event_ids in frontmatter and an embedded task
        content = "---\nevent_ids:\n  - retro-1\n---\n# Retro Notes\n\n- [ ] Follow up on action items\n"
        (data_dir / "notes" / "retro.md").write_text(content, encoding="utf-8")
        repo.reload()

        all_tasks = repo.list_tasks()
        note_tasks = [t for t in all_tasks if t.source_file == "notes/retro.md"]
        assert len(note_tasks) == 1
        # Task should inherit the note's event_ids
        assert "retro-1" in note_tasks[0].event_ids


# ── Granular reload ───────────────────────────────────────────────────────────


class TestGranularReload:
    def test_reload_for_changes_events_yaml(self, data_dir: Path, repo: Repository):
        # Write an event after the initial reload
        events_yaml = {
            "events": [{
                "id": "new-e1", "source": "local",
                "from": "2026-03-14T10:00", "to": "2026-03-14T11:00",
                "name": "New Event", "description": "", "participants": [], "location": "",
            }]
        }
        (data_dir / "events.yaml").write_text(
            yaml.dump(events_yaml, default_flow_style=False), encoding="utf-8"
        )
        repo.reload_for_changes(["events.yaml"])
        assert any(e.id == "new-e1" for e in repo.list_events())

    def test_reload_for_changes_note_file(self, data_dir: Path, repo: Repository):
        (data_dir / "notes" / "meeting.md").write_text(
            "# Team Meeting\n\nMinutes here.", encoding="utf-8"
        )
        repo.reload_for_changes(["notes/meeting.md"])
        notes = repo.list_notes()
        assert any(n.filename == "meeting.md" for n in notes)

    def test_reload_for_changes_unknown_path_is_noop(self, repo: Repository):
        # Should not raise
        repo.reload_for_changes(["unknown/path.txt"])
