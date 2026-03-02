"""Task service — domain operations for tasks.

Delegates to Repository for all data access and file I/O.
"""

from __future__ import annotations

from gera.entities import TaskEntity
from gera.repository import Repository


def list_tasks(repo: Repository) -> list[TaskEntity]:
    """Return all floating tasks (pre-resolved by the repository)."""
    return repo.list_tasks()


def search_tasks(repo: Repository, query: str) -> list[TaskEntity]:
    """Full-text search across tasks."""
    return repo.search_tasks(query)


def toggle_task(repo: Repository, source_file: str, line_number: int) -> None:
    """Toggle a task's completion status."""
    repo.toggle_task(source_file, line_number)
