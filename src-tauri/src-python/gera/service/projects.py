"""Project service — domain operations for projects.

Delegates to Repository for all data access and file I/O.
"""

from __future__ import annotations

from gera.entities import ProjectEntity
from gera.repository import Repository


def list_projects(repo: Repository) -> list[ProjectEntity]:
    """Return all projects."""
    return repo.list_projects()


def get_project(repo: Repository, project_id: str) -> ProjectEntity | None:
    """Return a single project by ID, or None."""
    return repo.get_project(project_id)


def search_projects(repo: Repository, query: str) -> list[ProjectEntity]:
    """Full-text search across projects."""
    return repo.search_projects(query)


def create_project(
    repo: Repository,
    filename: str,
    content: str,
    event_ids: list[str] | None = None,
) -> ProjectEntity:
    """Create a new project."""
    return repo.create_project(filename, content, event_ids=event_ids)


def update_project(repo: Repository, filename: str, content: str) -> ProjectEntity:
    """Update an existing project."""
    return repo.update_project(filename, content)


def delete_project(repo: Repository, filename: str) -> None:
    """Delete a project by filename."""
    repo.delete_project(filename)
