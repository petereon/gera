"""Shared fixtures for the Gera backend test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── Block pytauri and its sub-modules ────────────────────────────────────────
# pytauri requires the compiled Tauri Rust extension (gera.ext_mod) which is
# only present inside the actual Tauri runtime.  Mock it before any gera.*
# import so that gera/__init__.py (which re-exports gera.app.main) can load.
for _mod in [
    "pytauri",
    "pytauri.ffi",
    "pytauri.ffi._ext_mod",
    "pytauri.commands",
    "pytauri.event",
]:
    sys.modules.setdefault(_mod, MagicMock())

import pytest  # noqa: E402 — must come after sys.modules patching

from gera.repository import Repository  # noqa: E402


# ── Data directory fixture ────────────────────────────────────────────────────


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Minimal, valid Gera data directory with empty seed files."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "events.yaml").write_text("events: []\n", encoding="utf-8")
    (tmp_path / "tasks.md").write_text("", encoding="utf-8")
    return tmp_path


# ── Repository fixture ────────────────────────────────────────────────────────


@pytest.fixture
def repo(data_dir: Path) -> Repository:
    """Repository backed by a fresh tmp_path data directory.

    IMPORTANT: Repository uses file::memory:?cache=shared — all instances in
    the same process share one in-memory SQLite database.  Calling close() in
    teardown closes the keep-alive connection, which (in CPython) frees the
    in-memory DB so the next test starts with a clean slate.
    """
    r = Repository(data_dir)
    # Explicitly wipe all tables before each test.  Repository uses a shared
    # in-memory SQLite URI (file::memory:?cache=shared), so state survives across
    # fixture instances unless cleared.  reload() alone is insufficient when the
    # notes/projects dirs are empty — _replace_tasks() is a no-op for empty
    # source sets and leaves rows from the previous test in place.
    with r._conn() as db:
        for table in ("tasks", "notes", "projects", "events"):
            db.execute(f"DELETE FROM {table}")
        db.commit()
    r.reload()
    yield r
    r.close()
