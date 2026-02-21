"""YAML frontmatter parsing and serialization for Gera markdown files.

Gera notes and projects use YAML frontmatter delimited by ``---``:

    ---
    event_ids:
      - event-1
    project_ids:
      - project-1
    ---
    # My Note Title

    Body content here.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the markdown body.

    Args:
        content: Raw file content (may or may not have frontmatter).

    Returns:
        A ``(frontmatter_dict, body)`` tuple.
        If no frontmatter is found, returns ``({}, content)``.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    yaml_str = match.group(1)
    body = content[match.end() :]

    try:
        frontmatter = yaml.safe_load(yaml_str)
    except yaml.YAMLError:
        # If YAML is malformed, treat the whole file as body
        return {}, content

    if not isinstance(frontmatter, dict):
        return {}, content

    return frontmatter, body


def serialize_frontmatter(data: dict[str, Any], body: str) -> str:
    """Combine a frontmatter dict and markdown body into a complete file string.

    Args:
        data: Frontmatter key/value pairs. If empty, no ``---`` block is emitted.
        body: Markdown body content.

    Returns:
        Complete file content string.
    """
    if not data:
        return body

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False).strip()
    # Ensure exactly one newline between frontmatter and body
    body = body.lstrip("\n")
    return f"---\n{yaml_str}\n---\n\n{body}"
