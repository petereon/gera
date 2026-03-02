from typing import Callable
from pytauri import AppHandle, Emitter


def get_emit(handle: AppHandle) -> Callable[[str, str], None]:
    def _emit(event: str, payload: str) -> None:
        Emitter.emit_str(handle, event, payload)

    return _emit


def body_preview(body: str, max_len: int = 100) -> str:
    """First *max_len* characters of body text, stripped of leading headings/whitespace."""
    text = body.lstrip().removeprefix("#").lstrip()
    # Remove the first heading line
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            text = "\n".join(lines[i:])
            break
    return text[:max_len].strip()
