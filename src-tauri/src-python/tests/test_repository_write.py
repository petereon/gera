"""Tests for Repository write operations: CRUD for tasks, events, notes, projects."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from gera.entities import EventEntity, EventMetadata
from gera.repository import Repository


# ── Helpers ───────────────────────────────────────────────────────────────────


def _event(
    id: str = "e1",
    name: str = "Standup",
    from_: datetime = datetime(2026, 3, 14, 9, 0),
    to: datetime = datetime(2026, 3, 14, 9, 30),
) -> EventEntity:
    return EventEntity(
        id=id,
        source="local",
        from_=from_,
        to=to,
        name=name,
        description="",
        participants=[],
        location="",
        metadata=EventMetadata(),
    )


def tasks_file_content(data_dir: Path) -> str:
    return (data_dir / "tasks.md").read_text(encoding="utf-8")


def events_file_data(data_dir: Path) -> dict:
    return yaml.safe_load((data_dir / "events.yaml").read_text(encoding="utf-8"))


# ── Tasks — create ────────────────────────────────────────────────────────────


class TestCreateTask:
    def test_appends_task_line_to_file(self, data_dir: Path, repo: Repository):
        repo.create_task("Buy oat milk")
        content = tasks_file_content(data_dir)
        assert "- [ ] Buy oat milk" in content

    def test_returns_task_entity(self, repo: Repository):
        task = repo.create_task("New task")
        assert task.text == "New task"
        assert task.completed is False
        assert task.source_file == "tasks.md"

    def test_multiple_tasks_each_on_own_line(self, data_dir: Path, repo: Repository):
        repo.create_task("First")
        repo.create_task("Second")
        lines = [ln for ln in tasks_file_content(data_dir).splitlines() if ln.strip()]
        assert len(lines) == 2

    def test_empty_text_raises(self, repo: Repository):
        with pytest.raises(ValueError):
            repo.create_task("   ")

    def test_listed_after_creation(self, repo: Repository):
        repo.create_task("Visible task")
        tasks = [t for t in repo.list_tasks() if t.source_file == "tasks.md"]
        assert any(t.text == "Visible task" for t in tasks)


# ── Tasks — toggle ────────────────────────────────────────────────────────────


class TestToggleTask:
    def test_toggles_incomplete_to_complete(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Toggle me\n", encoding="utf-8")
        repo.reload_tasks()
        repo.toggle_task("tasks.md", 1)
        assert "- [x] Toggle me" in tasks_file_content(data_dir)

    def test_toggles_complete_to_incomplete(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [x] Already done\n", encoding="utf-8")
        repo.reload_tasks()
        repo.toggle_task("tasks.md", 1)
        assert "- [ ] Already done" in tasks_file_content(data_dir)

    def test_toggle_reflected_in_list(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Toggle me\n", encoding="utf-8")
        repo.reload_tasks()
        repo.toggle_task("tasks.md", 1)
        task = repo.list_tasks()[0]
        assert task.completed is True

    def test_toggle_invalid_line_raises_index_error(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] One task\n", encoding="utf-8")
        repo.reload_tasks()
        with pytest.raises(IndexError):
            repo.toggle_task("tasks.md", 99)

    def test_toggle_non_task_line_raises_value_error(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("# Not a task\n", encoding="utf-8")
        repo.reload_tasks()
        with pytest.raises(ValueError):
            repo.toggle_task("tasks.md", 1)

    def test_toggle_missing_file_raises_file_not_found(self, repo: Repository):
        with pytest.raises(FileNotFoundError):
            repo.toggle_task("nonexistent.md", 1)


# ── Tasks — update text ───────────────────────────────────────────────────────


class TestUpdateTask:
    def test_updates_task_text_in_file(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Old text\n", encoding="utf-8")
        repo.reload_tasks()
        repo.update_task("tasks.md", 1, "New text")
        assert "- [ ] New text" in tasks_file_content(data_dir)
        assert "Old text" not in tasks_file_content(data_dir)

    def test_preserves_completion_state(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [x] Completed task\n", encoding="utf-8")
        repo.reload_tasks()
        repo.update_task("tasks.md", 1, "Updated completed")
        assert "- [x] Updated completed" in tasks_file_content(data_dir)

    def test_reflected_in_list_after_update(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Before\n", encoding="utf-8")
        repo.reload_tasks()
        repo.update_task("tasks.md", 1, "After")
        assert repo.list_tasks()[0].text == "After"

    def test_empty_text_raises(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] A task\n", encoding="utf-8")
        repo.reload_tasks()
        with pytest.raises(ValueError):
            repo.update_task("tasks.md", 1, "   ")


# ── Tasks — delete ────────────────────────────────────────────────────────────


class TestDeleteTask:
    def test_removes_line_from_file(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Remove me\n", encoding="utf-8")
        repo.reload_tasks()
        repo.delete_task("tasks.md", 1)
        assert "Remove me" not in tasks_file_content(data_dir)

    def test_other_tasks_preserved(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Keep me\n- [ ] Delete me\n", encoding="utf-8")
        repo.reload_tasks()
        repo.delete_task("tasks.md", 2)
        content = tasks_file_content(data_dir)
        assert "Keep me" in content
        assert "Delete me" not in content

    def test_first_task_deletion(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] First\n- [ ] Second\n", encoding="utf-8")
        repo.reload_tasks()
        repo.delete_task("tasks.md", 1)
        content = tasks_file_content(data_dir)
        assert "First" not in content
        assert "Second" in content

    def test_delete_only_task_leaves_empty_file(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Solo\n", encoding="utf-8")
        repo.reload_tasks()
        repo.delete_task("tasks.md", 1)
        assert repo.list_tasks() == []

    def test_delete_invalid_line_raises_index_error(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] One\n", encoding="utf-8")
        repo.reload_tasks()
        with pytest.raises(IndexError):
            repo.delete_task("tasks.md", 99)

    def test_delete_non_task_line_raises_value_error(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("# Header\n", encoding="utf-8")
        repo.reload_tasks()
        with pytest.raises(ValueError):
            repo.delete_task("tasks.md", 1)


# ── Events — create ───────────────────────────────────────────────────────────


class TestCreateEvent:
    def test_creates_event_in_yaml(self, data_dir: Path, repo: Repository):
        repo.create_event(_event(id="standup", name="Standup"))
        data = events_file_data(data_dir)
        ids = [e["id"] for e in data["events"]]
        assert "standup" in ids

    def test_returns_created_entity(self, repo: Repository):
        created = repo.create_event(_event(id="e1", name="Retro"))
        assert created.id == "e1"
        assert created.name == "Retro"

    def test_visible_via_list_after_create(self, repo: Repository):
        repo.create_event(_event(id="e1"))
        assert any(e.id == "e1" for e in repo.list_events())

    def test_duplicate_id_raises(self, repo: Repository):
        repo.create_event(_event(id="e1"))
        with pytest.raises(FileExistsError):
            repo.create_event(_event(id="e1"))

    def test_multiple_events_coexist(self, repo: Repository):
        repo.create_event(_event(id="e1", name="A"))
        repo.create_event(_event(id="e2", name="B", from_=datetime(2026, 3, 14, 10, 0), to=datetime(2026, 3, 14, 11, 0)))
        assert len(repo.list_events()) == 2


# ── Events — update ───────────────────────────────────────────────────────────


class TestUpdateEvent:
    def test_updates_event_name_in_yaml(self, data_dir: Path, repo: Repository):
        repo.create_event(_event(id="e1", name="Old Name"))
        updated_evt = _event(id="e1", name="New Name")
        repo.update_event(updated_evt)
        data = events_file_data(data_dir)
        names = [e["name"] for e in data["events"]]
        assert "New Name" in names
        assert "Old Name" not in names

    def test_update_returns_updated_entity(self, repo: Repository):
        repo.create_event(_event(id="e1", name="Before"))
        result = repo.update_event(_event(id="e1", name="After"))
        assert result.name == "After"

    def test_update_missing_event_raises(self, repo: Repository):
        with pytest.raises(KeyError):
            repo.update_event(_event(id="no-such"))


# ── Events — delete ───────────────────────────────────────────────────────────


class TestDeleteEvent:
    def test_removes_event_from_yaml(self, data_dir: Path, repo: Repository):
        repo.create_event(_event(id="e1"))
        repo.delete_event("e1")
        data = events_file_data(data_dir)
        assert all(e.get("id") != "e1" for e in data["events"])

    def test_other_events_preserved(self, repo: Repository):
        repo.create_event(_event(id="e1", name="Keep"))
        repo.create_event(_event(id="e2", name="Delete", from_=datetime(2026, 3, 14, 10, 0), to=datetime(2026, 3, 14, 11, 0)))
        repo.delete_event("e2")
        ids = [e.id for e in repo.list_events()]
        assert "e1" in ids
        assert "e2" not in ids

    def test_delete_only_event_yields_empty_list(self, repo: Repository):
        repo.create_event(_event(id="e1"))
        repo.delete_event("e1")
        assert repo.list_events() == []

    def test_delete_missing_event_raises(self, repo: Repository):
        with pytest.raises(KeyError):
            repo.delete_event("no-such")


# ── Notes — create / update / delete ─────────────────────────────────────────


class TestNoteMutations:
    def test_create_note_creates_file(self, data_dir: Path, repo: Repository):
        repo.create_note("standup.md", "# Standup\n\nNotes here.")
        assert (data_dir / "notes" / "standup.md").exists()

    def test_create_note_returns_entity(self, repo: Repository):
        note = repo.create_note("retro.md", "# Retro\n\nWent well.")
        assert note.filename == "retro.md"
        assert note.title == "Retro"

    def test_create_note_visible_in_list(self, repo: Repository):
        repo.create_note("new.md", "# New\n\nContent.")
        assert any(n.filename == "new.md" for n in repo.list_notes())

    def test_create_duplicate_note_raises(self, repo: Repository):
        repo.create_note("dup.md", "# Dup\n")
        with pytest.raises(FileExistsError):
            repo.create_note("dup.md", "# Dup again\n")

    def test_update_note_changes_content(self, data_dir: Path, repo: Repository):
        repo.create_note("note.md", "# Before\n\nOld content.")
        repo.update_note("note.md", "# After\n\nNew content.")
        raw = (data_dir / "notes" / "note.md").read_text(encoding="utf-8")
        assert "New content." in raw
        assert "Old content." not in raw

    def test_update_note_reflected_in_list(self, repo: Repository):
        repo.create_note("note.md", "# Old Title\n\nBody.")
        repo.update_note("note.md", "# New Title\n\nBody.")
        note = repo.get_note("note.md")
        assert note is not None
        assert note.title == "New Title"

    def test_update_missing_note_raises(self, repo: Repository):
        with pytest.raises(FileNotFoundError):
            repo.update_note("ghost.md", "# Ghost\n")

    def test_delete_note_removes_file(self, data_dir: Path, repo: Repository):
        repo.create_note("del.md", "# Del\n\nBye.")
        repo.delete_note("del.md")
        assert not (data_dir / "notes" / "del.md").exists()

    def test_delete_note_not_in_list_after(self, repo: Repository):
        repo.create_note("del.md", "# Del\n\nBye.")
        repo.delete_note("del.md")
        assert all(n.filename != "del.md" for n in repo.list_notes())

    def test_delete_missing_note_raises(self, repo: Repository):
        with pytest.raises(FileNotFoundError):
            repo.delete_note("ghost.md")


# ── Sanitize content ─────────────────────────────────────────────────────────


class TestSanitizeContent:
    def test_html_encoded_space_stripped_from_line_end(self, data_dir: Path, repo: Repository):
        """&#x20; at end of lines must not be written to disk."""
        repo.create_note("note.md", "# Title\n\nContent&#x20;\n")
        raw = (data_dir / "notes" / "note.md").read_text(encoding="utf-8")
        # The &#x20; should be converted to a space then trailing spaces stripped
        assert "&#x20;" not in raw
