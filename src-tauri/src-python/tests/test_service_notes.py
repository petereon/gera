"""Tests for gera.service.notes — thin delegation layer over Repository."""

from __future__ import annotations


import gera.service.notes as svc
from gera.repository import Repository


class TestServiceNotes:
    def test_list_notes_empty(self, repo: Repository):
        assert svc.list_notes(repo) == []

    def test_create_note_returns_entity(self, repo: Repository):
        note = svc.create_note(repo, "standup.md", "# Standup\n\nNotes.")
        assert note.filename == "standup.md"
        assert note.title == "Standup"

    def test_created_note_appears_in_list(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Note\n\nContent.")
        assert any(n.filename == "note.md" for n in svc.list_notes(repo))

    def test_create_note_with_event_ids(self, repo: Repository):
        note = svc.create_note(repo, "note.md", "# Note\n", event_ids=["evt-1"])
        assert "evt-1" in note.event_ids

    def test_create_note_with_project_ids(self, repo: Repository):
        note = svc.create_note(repo, "note.md", "# Note\n", project_ids=["proj-1"])
        assert "proj-1" in note.project_ids

    def test_get_note_returns_entity(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Title\n\nBody.")
        note = svc.get_note(repo, "note.md")
        assert note is not None
        assert note.filename == "note.md"

    def test_get_note_returns_none_for_missing(self, repo: Repository):
        assert svc.get_note(repo, "ghost.md") is None

    def test_update_note_changes_title(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Old Title\n\nBody.")
        svc.update_note(repo, "note.md", "# New Title\n\nBody.")
        assert svc.get_note(repo, "note.md").title == "New Title"

    def test_delete_note_removes_it(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Note\n\nBye.")
        svc.delete_note(repo, "note.md")
        assert svc.get_note(repo, "note.md") is None

    def test_delete_note_not_in_list(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Note\n")
        svc.delete_note(repo, "note.md")
        assert all(n.filename != "note.md" for n in svc.list_notes(repo))

    def test_search_notes_finds_match(self, repo: Repository):
        svc.create_note(repo, "retro.md", "# Sprint Retro\n\nWent well.")
        svc.create_note(repo, "standup.md", "# Standup\n\nQuick sync.")
        results = svc.search_notes(repo, "Retro")
        assert len(results) == 1
        assert results[0].filename == "retro.md"

    def test_search_notes_by_body(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Note\n\nAction items from planning.")
        results = svc.search_notes(repo, "planning")
        assert len(results) == 1

    def test_search_notes_no_match(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Note\n\nSome content.")
        assert svc.search_notes(repo, "zzznomatch") == []

    def test_body_preview_is_populated(self, repo: Repository):
        svc.create_note(repo, "note.md", "# Title\n\nThis is preview text.")
        note = svc.get_note(repo, "note.md")
        assert note.body_preview != ""
        assert "preview" in note.body_preview
