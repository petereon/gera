"""Custom exceptions for Gera file I/O operations."""

from pathlib import Path


class GeraFileError(Exception):
    """Base exception for all Gera file system errors."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        super().__init__(message)


class DirectoryCreationError(GeraFileError):
    """Raised when a required directory cannot be created."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Failed to create directory '{path}': {reason}", path)


class FileReadError(GeraFileError):
    """Raised when a file cannot be read."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Failed to read '{path}': {reason}", path)


class FileWriteError(GeraFileError):
    """Raised when a file cannot be written."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Failed to write '{path}': {reason}", path)


class InvalidDataDirectoryError(GeraFileError):
    """Raised when the data directory path is invalid or inaccessible."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Invalid data directory '{path}': {reason}", path)
