"""Tests for gera.filesystem — data directory initialization and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from gera.errors import InvalidDataDirectoryError
from gera.filesystem import init_data_directory, verify_structure
from gera.paths import REQUIRED_DIRS


class TestInitDataDirectory:
    def test_creates_root_directory(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        assert target.is_dir()

    def test_creates_notes_and_projects_subdirs(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        assert (target / "notes").is_dir()
        assert (target / "projects").is_dir()

    def test_creates_events_yaml_with_empty_list(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        content = (target / "events.yaml").read_text(encoding="utf-8")
        assert "events:" in content

    def test_creates_tasks_md(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        assert (target / "tasks.md").exists()

    def test_idempotent_does_not_overwrite_existing_files(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        # Write custom content to events.yaml
        (target / "events.yaml").write_text("events:\n  - id: existing\n", encoding="utf-8")
        init_data_directory(target)
        content = (target / "events.yaml").read_text(encoding="utf-8")
        # Should still have the custom content, not be overwritten
        assert "existing" in content

    def test_returns_absolute_path(self, tmp_path: Path):
        target = tmp_path / "Gera"
        result = init_data_directory(target)
        assert result.is_absolute()
        assert result == target.resolve()

    def test_raises_if_path_is_a_file(self, tmp_path: Path):
        bad = tmp_path / "notadir"
        bad.write_text("I am a file", encoding="utf-8")
        with pytest.raises(InvalidDataDirectoryError):
            init_data_directory(bad)

    def test_all_required_dirs_created(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        for dirname in REQUIRED_DIRS:
            assert (target / dirname).is_dir(), f"Expected {dirname} to exist"


class TestVerifyStructure:
    def test_fully_initialized_dir_all_true(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        status = verify_structure(target)
        assert all(status.values()), f"Some items missing: {status}"

    def test_missing_notes_dir_reported(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        (target / "notes").rmdir()
        status = verify_structure(target)
        assert status["notes"] is False

    def test_missing_events_yaml_reported(self, tmp_path: Path):
        target = tmp_path / "Gera"
        init_data_directory(target)
        (target / "events.yaml").unlink()
        status = verify_structure(target)
        assert status["events.yaml"] is False

    def test_empty_dir_all_false_except_root(self, tmp_path: Path):
        target = tmp_path / "Empty"
        target.mkdir()
        status = verify_structure(target)
        assert status["."] is True
        assert status["notes"] is False
        assert status["projects"] is False
