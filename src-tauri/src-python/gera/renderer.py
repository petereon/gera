"""Markdown-to-HTML renderer with Gera-specific extensions.

Renders standard Markdown via *mistune* and post-processes the HTML to wrap
Gera-specific inline syntax in semantic ``<span>`` elements that the frontend
can style and attach behaviour to.

Handled Gera syntax (inside task items or body text):

* ``@before[2d]:event-1``  → prep-task reference with time offset
* ``@2026-3-3T18:00``      → standalone datetime deadline
* ``@event-1``             → direct event reference
* ``#project-id``          → project tag

The renderer also:

* Extracts YAML frontmatter (``event_ids``, ``project_ids``).
* Renders ``- [ ]`` / ``- [x]`` as interactive-looking checkboxes.
* Extracts the document title from the first ``# H1`` (or first few words).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import mistune

from gera.frontmatter import parse_frontmatter

# ---------------------------------------------------------------------------
# Gera reference patterns (applied as post-processing on rendered HTML)
# ---------------------------------------------------------------------------
# IMPORTANT: order matters — more specific patterns are applied first so that
# the less specific ones don't consume their prefixes.

# @before[OFFSET]:TARGET  (target = event-id or datetime)
_BEFORE_REF_RE = re.compile(r"@before\[(\d+[YMWDhm])\]:([\w][\w:.\-]*)")

# @DATETIME  e.g. @2026-3-3T18:00
_DATETIME_REF_RE = re.compile(r"@(\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2})")

# @EVENT-ID  (must NOT match @before[…] which is already handled)
_EVENT_REF_RE = re.compile(r"@(?!before\[)([a-zA-Z][\w\-]*)")

# #PROJECT-ID  (must start with a letter to avoid matching CSS hex colours)
_PROJECT_TAG_RE = re.compile(r"#([a-zA-Z][\w\-]*)")

# Title extraction from raw markdown
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------


def _replace_gera_refs(html: str) -> str:
    """Wrap Gera ``@``/``#`` references in semantic ``<span>`` elements."""

    # 1. @before[offset]:target
    html = _BEFORE_REF_RE.sub(
        r'<span class="gera-ref gera-ref--before" '
        r'data-offset="\1" data-target="\2">'
        r"@before[\1]:\2</span>",
        html,
    )

    # 2. @datetime
    html = _DATETIME_REF_RE.sub(
        r'<span class="gera-ref gera-ref--datetime" '
        r'data-datetime="\1">@\1</span>',
        html,
    )

    # 3. @event-id  (negative lookahead prevents double-matching @before)
    html = _EVENT_REF_RE.sub(
        r'<span class="gera-ref gera-ref--event" '
        r'data-event="\1">@\1</span>',
        html,
    )

    # 4. #project-id
    html = _PROJECT_TAG_RE.sub(
        r'<span class="gera-ref gera-ref--project" '
        r'data-project="\1">#\1</span>',
        html,
    )

    return html


def extract_title(body: str, fallback_words: int = 6) -> str:
    """Extract a display title from raw markdown.

    Uses the first ``# H1`` heading.  Falls back to the first *N* words.
    """
    match = _H1_RE.search(body)
    if match:
        return match.group(1).strip()
    words = body.split()[:fallback_words]
    return " ".join(words) if words else "Untitled"


# ---------------------------------------------------------------------------
# Mistune markdown renderer (singleton)
# ---------------------------------------------------------------------------


def _build_markdown() -> mistune.Markdown:
    """Create a mistune Markdown instance with task-list support."""
    # mistune v3 accepts plugin names as strings
    try:
        md = mistune.create_markdown(
            # Escape raw HTML from markdown input to avoid direct HTML injection.
            escape=True,
            plugins=["task_lists", "strikethrough", "table"],
        )
    except Exception:
        # Fallback: no plugins if mistune version doesn't support string names
        md = mistune.create_markdown(escape=True)
    return md


_md = _build_markdown()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class RenderedDocument:
    """Result of rendering a Gera markdown document."""

    frontmatter: dict[str, Any]
    """Parsed YAML frontmatter (``event_ids``, ``project_ids``, etc.)."""

    html: str
    """Fully rendered HTML body with Gera reference spans."""

    title: str
    """Display title extracted from H1 or first words."""

    event_ids: list[str]
    """Convenience: ``event_ids`` pulled from frontmatter (empty list if absent)."""

    project_ids: list[str]
    """Convenience: ``project_ids`` pulled from frontmatter (empty list if absent)."""


def render(content: str) -> RenderedDocument:
    """Render a Gera markdown document to HTML.

    Args:
        content: Raw file content (may include YAML frontmatter).

    Returns:
        A :class:`RenderedDocument` with parsed metadata and rendered HTML.
    """
    frontmatter, body = parse_frontmatter(content)
    title = extract_title(body)

    # Standard markdown → HTML
    html = str(_md(body))

    # Gera-specific post-processing
    html = _replace_gera_refs(html)

    return RenderedDocument(
        frontmatter=frontmatter,
        html=html,
        title=title,
        event_ids=frontmatter.get("event_ids", []) or [],
        project_ids=frontmatter.get("project_ids", []) or [],
    )


def render_body(markdown_body: str) -> str:
    """Render a markdown string (no frontmatter) to HTML with Gera refs.

    Useful when you already have the body separated from frontmatter.
    """
    html = str(_md(markdown_body))
    return _replace_gera_refs(html)
