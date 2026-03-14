"""Tests for gera.service.tasks — thin delegation layer over Repository."""

from __future__ import annotations

from pathlib import Path


import gera.service.tasks as svc
from gera.repository import Repository


class TestServiceTasks:
    def test_list_tasks_empty(self, repo: Repository):
        assert svc.list_tasks(repo) == []

    def test_create_task_returns_entity(self, repo: Repository):
        task = svc.create_task(repo, "Write tests")
        assert task.text == "Write tests"
        assert task.completed is False

    def test_created_task_appears_in_list(self, repo: Repository):
        svc.create_task(repo, "Visible task")
        tasks = svc.list_tasks(repo)
        assert any(t.text == "Visible task" for t in tasks)

    def test_toggle_task_changes_completion(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Toggle me\n", encoding="utf-8")
        repo.reload_tasks()
        task = svc.list_tasks(repo)[0]
        svc.toggle_task(repo, task.source_file, task.line_number)
        updated = svc.list_tasks(repo)[0]
        assert updated.completed is True

    def test_update_task_changes_text(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Old text\n", encoding="utf-8")
        repo.reload_tasks()
        task = svc.list_tasks(repo)[0]
        svc.update_task(repo, task.source_file, task.line_number, "New text")
        assert svc.list_tasks(repo)[0].text == "New text"

    def test_delete_task_removes_it(self, data_dir: Path, repo: Repository):
        (data_dir / "tasks.md").write_text("- [ ] Delete me\n", encoding="utf-8")
        repo.reload_tasks()
        task = svc.list_tasks(repo)[0]
        svc.delete_task(repo, task.source_file, task.line_number)
        assert svc.list_tasks(repo) == []

    def test_search_tasks_finds_match(self, repo: Repository):
        svc.create_task(repo, "Review the slides")
        svc.create_task(repo, "Buy groceries")
        results = svc.search_tasks(repo, "slides")
        assert len(results) == 1
        assert results[0].text == "Review the slides"

    def test_search_tasks_no_match(self, repo: Repository):
        svc.create_task(repo, "Something else")
        assert svc.search_tasks(repo, "zzznomatch") == []
