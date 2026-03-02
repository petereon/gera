"""File-system watcher for the Gera data directory.

Monitors ``~/Documents/Gera`` (or the configured data root) for changes
and emits a ``gera://fs-changed`` Tauri event so the frontend can reload.

The watcher runs in a background thread and debounces rapid changes
(e.g. editor save → tmp-file → rename) into a single event.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from watchfiles import Change, watch

logger = logging.getLogger(__name__)

# Tauri event name the frontend subscribes to
EVENT_NAME = "gera://fs-changed"

# Only watch files with these suffixes
_WATCHED_SUFFIXES = frozenset((".yaml", ".yml", ".md"))


@dataclass
class WatcherHandle:
    """Runtime handle for a running watcher thread."""

    thread: threading.Thread
    stop_event: threading.Event


def _change_type_label(change: Change) -> str:
    return {
        Change.added: "added",
        Change.modified: "modified",
        Change.deleted: "deleted",
    }.get(change, "unknown")


def _start_watcher(data_root: Path, emit_fn: object) -> WatcherHandle:
    """Launch the directory watcher in a daemon thread.

    Args:
        data_root: The Gera data directory to monitor.
        emit_fn:   A callable ``(event_name: str, json_payload: str) -> None``
                   that pushes events to the frontend.  In practice this is
                   a partial of ``Emitter.emit_str`` bound to the ``AppHandle``.

    Returns:
        A watcher handle containing the daemon thread and a stop signal.
    """

    stop_event = threading.Event()

    def _watch_loop() -> None:
        logger.info("File watcher started on %s", data_root)
        try:
            for changeset in watch(
                data_root,
                # watchfiles debounce_ms defaults to 1600 which is too slow;
                # 300 ms is responsive but still coalesces burst writes.
                debounce=300,
                recursive=True,
                stop_event=stop_event,
            ):
                # Filter to files we care about
                relevant: list[dict[str, str]] = []
                for change, path_str in changeset:
                    p = Path(path_str)
                    if p.suffix.lower() in _WATCHED_SUFFIXES:
                        relevant.append(
                            {
                                "type": _change_type_label(change),
                                "path": str(p.relative_to(data_root)),
                            }
                        )

                if not relevant:
                    continue

                payload = json.dumps({"changes": relevant})
                logger.debug("fs-changed: %s", payload)
                try:
                    emit_fn(EVENT_NAME, payload)  # type: ignore[operator]
                except Exception:
                    logger.warning("Failed to emit fs-changed event", exc_info=True)
        except Exception:
            logger.exception("File watcher crashed")
        finally:
            logger.info("File watcher stopped")

    thread = threading.Thread(target=_watch_loop, name="gera-fs-watcher", daemon=True)
    thread.start()
    return WatcherHandle(thread=thread, stop_event=stop_event)


def _stop_watcher(handle: WatcherHandle, timeout: float = 1.0) -> None:
    """Signal watcher shutdown and wait briefly for thread exit."""
    handle.stop_event.set()
    handle.thread.join(timeout=timeout)
