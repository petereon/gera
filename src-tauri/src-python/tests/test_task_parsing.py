"""Tests for task-line parsing (Gera syntax) via Repository._parse_tasks_from_markdown."""

from __future__ import annotations

import pytest

from gera.repository import Repository


# Helpers — call the private parser directly (it performs no I/O)
def parse(text: str, source_file: str = "tasks.md"):
    """Call Repository._parse_tasks_from_markdown without a full repo."""
    # We need a Repository instance only for its method; we pass a dummy path
    # that need not exist since _parse_tasks_from_markdown does no I/O.
    from pathlib import Path
    r = Repository.__new__(Repository)
    return r._parse_tasks_from_markdown(text, source_file=source_file)


# ── Basic checkbox parsing ─────────────────────────────────────────────────────


class TestBasicParsing:
    def test_incomplete_task(self):
        tasks = parse("- [ ] Buy milk\n")
        assert len(tasks) == 1
        assert tasks[0].text == "Buy milk"
        assert tasks[0].completed is False

    def test_completed_task_lowercase_x(self):
        tasks = parse("- [x] Done thing\n")
        assert tasks[0].completed is True

    def test_completed_task_uppercase_x(self):
        tasks = parse("- [X] Also done\n")
        assert tasks[0].completed is True

    def test_star_bullet(self):
        tasks = parse("* [ ] Star bullet task\n")
        assert len(tasks) == 1
        assert tasks[0].text == "Star bullet task"

    def test_plus_bullet(self):
        tasks = parse("+ [ ] Plus bullet task\n")
        assert len(tasks) == 1

    def test_non_task_line_skipped(self):
        tasks = parse("Just a regular paragraph.\n")
        assert tasks == []

    def test_heading_line_skipped(self):
        tasks = parse("# Tasks\n- [ ] Real task\n")
        assert len(tasks) == 1
        assert tasks[0].text == "Real task"

    def test_multiple_tasks(self):
        md = "- [ ] First\n- [x] Second\n- [ ] Third\n"
        tasks = parse(md)
        assert len(tasks) == 3
        assert [t.text for t in tasks] == ["First", "Second", "Third"]

    def test_line_numbers_are_1_based(self):
        md = "# Header\n- [ ] Task one\n- [ ] Task two\n"
        tasks = parse(md)
        assert tasks[0].line_number == 2
        assert tasks[1].line_number == 3

    def test_source_file_propagated(self):
        tasks = parse("- [ ] A task\n", source_file="notes/standup.md")
        assert tasks[0].source_file == "notes/standup.md"

    def test_raw_line_preserved(self):
        line = "- [ ] Buy milk\n"
        tasks = parse(line)
        assert tasks[0].raw_line == "- [ ] Buy milk"


# ── Event references ──────────────────────────────────────────────────────────


class TestEventReferences:
    def test_plain_event_ref(self):
        tasks = parse("- [ ] Prep for @standup\n")
        assert "standup" in tasks[0].event_ids

    def test_event_ref_with_hyphens(self):
        tasks = parse("- [ ] Prep @sprint-retro-q1\n")
        assert "sprint-retro-q1" in tasks[0].event_ids

    def test_multiple_event_refs(self):
        tasks = parse("- [ ] Attend @standup and @retro\n")
        assert "standup" in tasks[0].event_ids
        assert "retro" in tasks[0].event_ids

    def test_no_event_ref(self):
        tasks = parse("- [ ] Plain task\n")
        assert tasks[0].event_ids == []


# ── Project references ────────────────────────────────────────────────────────


class TestProjectReferences:
    def test_plain_project_ref(self):
        tasks = parse("- [ ] Work on #atlas\n")
        assert "atlas" in tasks[0].project_ids

    def test_multiple_project_refs(self):
        tasks = parse("- [ ] Task for #atlas and #gera\n")
        assert "atlas" in tasks[0].project_ids
        assert "gera" in tasks[0].project_ids

    def test_no_project_ref(self):
        tasks = parse("- [ ] No project\n")
        assert tasks[0].project_ids == []


# ── Absolute datetime deadline ────────────────────────────────────────────────


class TestDeadlineParsing:
    def test_absolute_datetime_becomes_deadline(self):
        tasks = parse("- [ ] Submit report @2026-03-20T09:00\n")
        assert tasks[0].deadline is not None
        assert tasks[0].deadline.year == 2026
        assert tasks[0].deadline.month == 3
        assert tasks[0].deadline.day == 20
        assert tasks[0].deadline.hour == 9

    def test_no_deadline_when_absent(self):
        tasks = parse("- [ ] Plain task\n")
        assert tasks[0].deadline is None


# ── Time references (@before / @after) ────────────────────────────────────────


class TestTimeReferences:
    def test_before_minutes(self):
        tasks = parse("- [ ] Prep @before[30m]:standup\n")
        refs = tasks[0].time_references
        assert len(refs) == 1
        assert refs[0].modifier == "before"
        assert refs[0].amount == 30
        assert refs[0].unit == "m"
        assert refs[0].target_id == "standup"

    def test_before_adds_event_id(self):
        tasks = parse("- [ ] Prep @before[30m]:standup\n")
        assert "standup" in tasks[0].event_ids

    def test_after_days(self):
        tasks = parse("- [ ] Follow up @after[2d]:retro\n")
        refs = tasks[0].time_references
        assert refs[0].modifier == "after"
        assert refs[0].amount == 2
        assert refs[0].unit == "d"
        assert refs[0].target_id == "retro"

    def test_before_weeks(self):
        tasks = parse("- [ ] Plan @before[1W]:sprint-kickoff\n")
        refs = tasks[0].time_references
        assert refs[0].unit == "W"
        assert refs[0].amount == 1

    def test_multiple_time_refs(self):
        tasks = parse("- [ ] Task @before[1d]:evt-a @after[2h]:evt-b\n")
        refs = tasks[0].time_references
        assert len(refs) == 2
        modifiers = {r.modifier for r in refs}
        assert modifiers == {"before", "after"}


# ── Mixed syntax ──────────────────────────────────────────────────────────────


class TestMixedSyntax:
    def test_event_project_and_deadline_together(self):
        tasks = parse("- [ ] Submit @2026-03-20T09:00 @standup #atlas\n")
        t = tasks[0]
        assert t.deadline is not None
        assert "standup" in t.event_ids
        assert "atlas" in t.project_ids

    def test_completed_with_all_refs(self):
        tasks = parse("- [x] Done @before[1d]:retro #gera\n")
        t = tasks[0]
        assert t.completed is True
        assert len(t.time_references) == 1
        assert "gera" in t.project_ids
