from typing import Callable
from pytauri import AppHandle, Emitter


def get_emit(handle: AppHandle) -> Callable[[str, str], None]:
    def _emit(event: str, payload: str) -> None:
        Emitter.emit_str(handle, event, payload)

    return _emit


def body_preview(body: str, max_len: int = 100) -> str:
    """First *max_len* characters of body text, skipping only the leading title heading."""
    lines = body.splitlines()
    # Skip consecutive heading lines at the top (the title block)
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("#"):
        i += 1
    text = "\n".join(lines[i:]).strip()
    return text[:max_len].strip()
