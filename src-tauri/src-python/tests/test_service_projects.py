"""Tests for gera.service.projects — thin delegation layer over Repository."""

from __future__ import annotations

import pytest

import gera.service.projects as svc
from gera.repository import Repository


class TestServiceProjects:
    def test_list_projects_empty(self, repo: Repository):
        assert svc.list_projects(repo) == []

    def test_create_project_returns_entity(self, repo: Repository):
        proj = svc.create_project(repo, "atlas.md", "Build the thing.")
        assert proj.id == "atlas"
        assert proj.filename == "atlas.md"

    def test_created_project_appears_in_list(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Build the thing.")
        assert any(p.id == "atlas" for p in svc.list_projects(repo))

    def test_create_project_with_event_ids(self, repo: Repository):
        proj = svc.create_project(repo, "atlas.md", "Content.", event_ids=["kickoff"])
        assert "kickoff" in proj.event_ids

    def test_get_project_returns_entity(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Content.")
        proj = svc.get_project(repo, "atlas")
        assert proj is not None
        assert proj.id == "atlas"

    def test_get_project_returns_none_for_missing(self, repo: Repository):
        assert svc.get_project(repo, "no-such") is None

    def test_title_extracted_from_h1(self, repo: Repository):
        # create_project prepends "# <stem>" automatically
        proj = svc.create_project(repo, "atlas.md", "More content.")
        assert proj.title == "atlas"

    def test_update_project_changes_content(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Old content.")
        svc.update_project(repo, "atlas.md", "# atlas\n\nNew content.")
        proj = svc.get_project(repo, "atlas")
        assert "New content." in proj.raw_content

    def test_delete_project_removes_it(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Content.")
        svc.delete_project(repo, "atlas.md")
        assert svc.get_project(repo, "atlas") is None

    def test_delete_project_not_in_list(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Content.")
        svc.delete_project(repo, "atlas.md")
        assert all(p.id != "atlas" for p in svc.list_projects(repo))

    def test_search_projects_finds_match(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Big infrastructure project.")
        svc.create_project(repo, "hermes.md", "Messaging service.")
        results = svc.search_projects(repo, "infrastructure")
        assert len(results) == 1
        assert results[0].id == "atlas"

    def test_search_projects_no_match(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "Content.")
        assert svc.search_projects(repo, "zzznomatch") == []

    def test_body_preview_populated(self, repo: Repository):
        svc.create_project(repo, "atlas.md", "This is the preview content here.")
        proj = svc.get_project(repo, "atlas")
        assert proj.body_preview != ""
