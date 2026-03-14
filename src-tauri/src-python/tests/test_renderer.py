"""Tests for gera.renderer — Markdown → HTML with Gera reference spans."""

from __future__ import annotations


from gera.renderer import RenderedDocument, extract_title, render, render_body


# ── extract_title ─────────────────────────────────────────────────────────────


class TestExtractTitle:
    def test_h1_heading_used_as_title(self):
        assert extract_title("# Sprint Retro\n\nBody") == "Sprint Retro"

    def test_h1_stripped_of_whitespace(self):
        assert extract_title("#  Leading spaces  \n") == "Leading spaces"

    def test_h2_not_used_as_title(self):
        title = extract_title("## Section\n\nBody")
        # Falls back to first N words of body — should strip Markdown syntax
        assert title != ""
        assert "##" not in title

    def test_no_heading_falls_back_to_first_words(self):
        title = extract_title("One two three four five six seven eight")
        assert title == "One two three four five six"

    def test_empty_body_returns_untitled(self):
        assert extract_title("") == "Untitled"

    def test_whitespace_only_body_returns_untitled(self):
        assert extract_title("   \n\n   ") == "Untitled"

    def test_h1_not_at_start_of_file(self):
        body = "Intro paragraph.\n\n# Real Title\n\nMore."
        assert extract_title(body) == "Real Title"


# ── render_body ───────────────────────────────────────────────────────────────


class TestRenderBody:
    def test_plain_markdown_heading(self):
        html = render_body("# Hello")
        assert "<h1" in html
        assert "Hello" in html

    def test_bold_and_italic(self):
        html = render_body("**bold** and *italic*")
        assert "<strong>" in html
        assert "<em>" in html

    def test_inline_code(self):
        html = render_body("Use `print()` here")
        assert "<code>" in html

    def test_unordered_list(self):
        html = render_body("- item one\n- item two")
        assert "<ul>" in html or "<li>" in html

    def test_empty_string_returns_empty_or_whitespace(self):
        html = render_body("")
        assert html.strip() == ""

    def test_plain_text_wrapped_in_paragraph(self):
        html = render_body("Just some text.")
        assert "<p>" in html

    # ── Gera reference spans ──────────────────────────────────────────────

    def test_event_ref_wrapped_in_span(self):
        html = render_body("See @standup-jan-20 for details")
        assert 'class="gera-ref gera-ref--event"' in html
        assert 'data-event="standup-jan-20"' in html

    def test_project_tag_wrapped_in_span(self):
        html = render_body("Part of #atlas project")
        assert 'class="gera-ref gera-ref--project"' in html
        assert 'data-project="atlas"' in html

    def test_before_ref_wrapped_in_span(self):
        html = render_body("Prep @before[2d]:standup")
        assert 'class="gera-ref gera-ref--before"' in html
        assert 'data-offset="2d"' in html
        assert 'data-target="standup"' in html

    def test_datetime_ref_wrapped_in_span(self):
        html = render_body("Due @2026-03-20T09:00")
        assert 'class="gera-ref gera-ref--datetime"' in html
        assert 'data-datetime="2026-03-20T09:00"' in html

    def test_before_ref_not_double_matched_by_event_ref(self):
        html = render_body("@before[1h]:standup")
        # Must NOT produce a gera-ref--event span for "before"
        assert html.count("gera-ref--before") == 1
        assert 'data-event="before"' not in html


# ── render (full document) ────────────────────────────────────────────────────


class TestRender:
    def test_returns_rendered_document(self):
        doc = render("# My Note\n\nBody text.")
        assert isinstance(doc, RenderedDocument)

    def test_title_extracted(self):
        doc = render("# Sprint Retro\n\nBody.")
        assert doc.title == "Sprint Retro"

    def test_frontmatter_event_ids_populated(self):
        content = "---\nevent_ids:\n  - evt-1\n---\n# Note\n"
        doc = render(content)
        assert doc.event_ids == ["evt-1"]
        assert doc.frontmatter["event_ids"] == ["evt-1"]

    def test_frontmatter_project_ids_populated(self):
        content = "---\nproject_ids:\n  - atlas\n---\n# Note\n"
        doc = render(content)
        assert doc.project_ids == ["atlas"]

    def test_no_frontmatter_gives_empty_ids(self):
        doc = render("# Simple Note\n\nNo frontmatter.")
        assert doc.event_ids == []
        assert doc.project_ids == []

    def test_html_contains_rendered_body(self):
        doc = render("# Title\n\n**Bold** text.")
        assert "<strong>" in doc.html

    def test_gera_refs_in_full_render(self):
        doc = render("# Note\n\nLinked to @standup #atlas")
        assert "gera-ref--event" in doc.html
        assert "gera-ref--project" in doc.html
