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
from pathlib import Path

from watchfiles import Change, watch

logger = logging.getLogger(__name__)

# Tauri event name the frontend subscribes to
EVENT_NAME = "gera://fs-changed"

# Only watch files with these suffixes
_WATCHED_SUFFIXES = frozenset((".yaml", ".yml", ".md"))


def _change_type_label(change: Change) -> str:
    return {Change.added: "added", Change.modified: "modified", Change.deleted: "deleted"}.get(
        change, "unknown"
    )


def _start_watcher(data_root: Path, emit_fn: object) -> threading.Thread:
    """Launch the directory watcher in a daemon thread.

    Args:
        data_root: The Gera data directory to monitor.
        emit_fn:   A callable ``(event_name: str, json_payload: str) -> None``
                   that pushes events to the frontend.  In practice this is
                   a partial of ``Emitter.emit_str`` bound to the ``AppHandle``.

    Returns:
        The started daemon ``Thread`` (kept for optional join on shutdown).
    """

    def _watch_loop() -> None:
        logger.info("File watcher started on %s", data_root)
        try:
            for changeset in watch(
                data_root,
                # watchfiles debounce_ms defaults to 1600 which is too slow;
                # 300 ms is responsive but still coalesces burst writes.
                debounce=300,
                recursive=True,
                # Stop gracefully when main thread exits
                stop_event=threading.Event(),  # never set — daemon thread dies with process
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

    thread = threading.Thread(target=_watch_loop, name="gera-fs-watcher", daemon=True)
    thread.start()
    return thread
