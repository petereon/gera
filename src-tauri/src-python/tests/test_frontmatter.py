"""Tests for gera.frontmatter — YAML frontmatter parsing and serialization."""

from __future__ import annotations


from gera.frontmatter import parse_frontmatter, serialize_frontmatter


# ── parse_frontmatter ─────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_dict_and_full_content(self):
        content = "# My Note\n\nBody text."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parses_event_ids_and_project_ids(self):
        content = "---\nevent_ids:\n  - evt-1\nproject_ids:\n  - proj-1\n---\n# Title\n"
        fm, body = parse_frontmatter(content)
        assert fm["event_ids"] == ["evt-1"]
        assert fm["project_ids"] == ["proj-1"]
        assert "# Title" in body

    def test_body_does_not_include_frontmatter_block(self):
        content = "---\nkey: value\n---\nBody here."
        _fm, body = parse_frontmatter(content)
        assert "---" not in body
        assert body.strip() == "Body here."

    def test_empty_frontmatter_block_returns_empty_dict(self):
        content = "---\n---\n# Body"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert "# Body" in body

    def test_malformed_yaml_treats_whole_file_as_body(self):
        content = "---\n: invalid: yaml: {[\n---\n# Body"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_multiple_event_ids_preserved(self):
        content = "---\nevent_ids:\n  - a\n  - b\n  - c\n---\nBody"
        fm, _body = parse_frontmatter(content)
        assert fm["event_ids"] == ["a", "b", "c"]

    def test_unicode_in_frontmatter_and_body(self):
        content = "---\ntitle: Ünïcödé\n---\n# Héllo Wörld"
        fm, body = parse_frontmatter(content)
        assert fm["title"] == "Ünïcödé"
        assert "Héllo" in body

    def test_non_dict_yaml_returns_empty_dict(self):
        # YAML that parses to a list, not a dict
        content = "---\n- item1\n- item2\n---\nBody"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content


# ── serialize_frontmatter ─────────────────────────────────────────────────────


class TestSerializeFrontmatter:
    def test_empty_dict_returns_body_only(self):
        result = serialize_frontmatter({}, "# My Note\n")
        assert result == "# My Note\n"
        assert "---" not in result

    def test_produces_valid_yaml_block(self):
        result = serialize_frontmatter({"event_ids": ["evt-1"]}, "# Title\n")
        assert result.startswith("---\n")
        assert "event_ids:" in result
        assert "---\n" in result

    def test_body_follows_frontmatter_with_blank_line(self):
        result = serialize_frontmatter({"key": "val"}, "# Title\n")
        # Should be: ---\n...\n---\n\n# Title
        parts = result.split("---\n")
        # parts[0] = '', parts[1] = yaml, parts[2] = '\n# Title\n'
        assert parts[2].startswith("\n")

    def test_round_trip_preserves_event_and_project_ids(self):
        original = {"event_ids": ["e1", "e2"], "project_ids": ["p1"]}
        body = "# Note\n\nContent here."
        serialized = serialize_frontmatter(original, body)
        fm, recovered_body = parse_frontmatter(serialized)
        assert fm["event_ids"] == ["e1", "e2"]
        assert fm["project_ids"] == ["p1"]
        assert "Content here." in recovered_body

    def test_leading_newlines_stripped_from_body(self):
        result = serialize_frontmatter({"k": "v"}, "\n\n# Title")
        # Body should not have leading blank lines after the --- block
        after_fm = result.split("---\n", 2)[-1]
        assert not after_fm.startswith("\n\n\n")
