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


def create_task(repo: Repository, text: str) -> TaskEntity:
    """Create a new floating task in tasks.md."""
    return repo.create_task(text)


def update_task(repo: Repository, source_file: str, line_number: int, new_text: str) -> None:
    """Update the text of an existing task."""
    repo.update_task(source_file, line_number, new_text)


def delete_task(repo: Repository, source_file: str, line_number: int) -> None:
    """Delete a task line from its source file."""
    repo.delete_task(source_file, line_number)
