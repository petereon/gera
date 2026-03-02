"""Service layer — domain operations.

Re-exports service functions so callers can do::

    from gera.service import events, notes, projects, tasks
"""

from gera.service import events, notes, projects, tasks

__all__ = [
    "events",
    "notes",
    "projects",
    "tasks",
]
