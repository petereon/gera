"""Tests for gera.service.google_calendar — sync logic and HTTP interactions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gera.entities import EventEntity, EventMetadata
from gera.repository import Repository
from gera.service.google_calendar import (
    SyncResult,
    _parse_gcal_datetime,
    fetch_google_events,
    google_event_to_entity,
    refresh_access_token,
    sync_google_events,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

ACCOUNT = "user@example.com"
CALENDAR = "primary"


def _mock_response(body: dict, status: int = 200) -> MagicMock:
    """Return a mock that behaves like urllib.request.urlopen's response."""
    mock = MagicMock()
    mock.read.return_value = json.dumps(body).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _gcal_event(
    id: str = "gcal-123",
    summary: str = "Standup",
    start: str = "2026-03-14T09:00:00Z",
    end: str = "2026-03-14T09:30:00Z",
    etag: str = '"etag-abc"',
    recurring_event_id: str = "",
) -> dict:
    evt = {
        "id": id,
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "etag": etag,
        "attendees": [],
    }
    if recurring_event_id:
        evt["recurringEventId"] = recurring_event_id
    return evt


def _local_event(
    id: str = "e1",
    name: str = "Standup",
    source_event_id: str = "gcal-123",
    etag: str = '"etag-abc"',
) -> EventEntity:
    return EventEntity(
        id=id,
        source="google_calendar",
        from_=datetime(2026, 3, 14, 9, 0),
        to=datetime(2026, 3, 14, 9, 30),
        name=name,
        description="",
        participants=[],
        location="",
        metadata=EventMetadata(
            source_platform="google_calendar",
            source_account=ACCOUNT,
            source_event_id=source_event_id,
            source_calendar_id=CALENDAR,
            etag=etag,
        ),
    )


# ── _parse_gcal_datetime ──────────────────────────────────────────────────────


class TestParseGcalDatetime:
    def test_rfc3339_with_z(self):
        dt = _parse_gcal_datetime("2026-03-14T09:00:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.hour == 9

    def test_rfc3339_with_offset(self):
        dt = _parse_gcal_datetime("2026-03-14T09:00:00+01:00")
        assert dt is not None

    def test_date_only(self):
        dt = _parse_gcal_datetime("2026-03-14")
        assert dt is not None
        assert dt.day == 14

    def test_none_returns_none(self):
        assert _parse_gcal_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_gcal_datetime("") is None

    def test_garbage_returns_none(self):
        assert _parse_gcal_datetime("not-a-date") is None


# ── google_event_to_entity ────────────────────────────────────────────────────


class TestGoogleEventToEntity:
    def test_converts_basic_event(self):
        raw = _gcal_event(id="abc", summary="Sprint Retro")
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert entity is not None
        assert entity.name == "Sprint Retro"
        assert entity.source == "google_calendar"

    def test_id_is_derived_from_account_and_source_id(self):
        raw = _gcal_event(id="abc123")
        entity = google_event_to_entity(raw, "user@example.com", CALENDAR)
        assert entity is not None
        assert "user_example.com" in entity.id
        assert "abc123" in entity.id

    def test_metadata_populated(self):
        raw = _gcal_event(id="abc", etag='"etag-xyz"')
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert entity.metadata.source_platform == "google_calendar"
        assert entity.metadata.source_account == ACCOUNT
        assert entity.metadata.source_event_id == "abc"
        assert entity.metadata.etag == '"etag-xyz"'

    def test_participants_extracted(self):
        raw = _gcal_event()
        raw["attendees"] = [
            {"email": "alice@example.com"},
            {"email": "bob@example.com"},
        ]
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert "alice@example.com" in entity.participants

    def test_missing_start_returns_none(self):
        raw = _gcal_event()
        raw["start"] = {}
        assert google_event_to_entity(raw, ACCOUNT, CALENDAR) is None

    def test_missing_end_returns_none(self):
        raw = _gcal_event()
        raw["end"] = {}
        assert google_event_to_entity(raw, ACCOUNT, CALENDAR) is None

    def test_all_day_event_uses_date_field(self):
        raw = _gcal_event()
        raw["start"] = {"date": "2026-03-14"}
        raw["end"] = {"date": "2026-03-15"}
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert entity is not None
        assert entity.from_.day == 14

    def test_recurring_event_id_stored(self):
        raw = _gcal_event(recurring_event_id="master-event-id")
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert entity.metadata.recurring_event_id == "master-event-id"

    def test_no_title_uses_fallback(self):
        raw = _gcal_event()
        del raw["summary"]
        entity = google_event_to_entity(raw, ACCOUNT, CALENDAR)
        assert entity is not None
        assert entity.name == "(No title)"


# ── fetch_google_events ───────────────────────────────────────────────────────


class TestFetchGoogleEvents:
    def test_returns_items_from_single_page(self):
        response = _mock_response({"items": [_gcal_event()]})
        with patch("gera.service.google_calendar.urllib.request.urlopen", return_value=response):
            events = fetch_google_events("token", ACCOUNT)
        assert len(events) == 1

    def test_follows_next_page_token(self):
        page1 = _mock_response({"items": [_gcal_event(id="e1")], "nextPageToken": "tok2"})
        page2 = _mock_response({"items": [_gcal_event(id="e2")]})
        with patch(
            "gera.service.google_calendar.urllib.request.urlopen",
            side_effect=[page1, page2],
        ):
            events = fetch_google_events("token", ACCOUNT)
        assert len(events) == 2
        ids = {e["id"] for e in events}
        assert ids == {"e1", "e2"}

    def test_empty_items_returns_empty_list(self):
        response = _mock_response({"items": []})
        with patch("gera.service.google_calendar.urllib.request.urlopen", return_value=response):
            events = fetch_google_events("token", ACCOUNT)
        assert events == []

    def test_http_error_raises_value_error(self):
        import urllib.error

        http_err = urllib.error.HTTPError(
            url="https://example.com",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b"Unauthorized"),
        )
        with patch(
            "gera.service.google_calendar.urllib.request.urlopen",
            side_effect=http_err,
        ):
            with pytest.raises(ValueError, match="401"):
                fetch_google_events("bad-token", ACCOUNT)

    def test_authorization_header_sent(self):
        response = _mock_response({"items": []})
        with patch(
            "gera.service.google_calendar.urllib.request.urlopen", return_value=response
        ) as mock_open:
            fetch_google_events("my-token", ACCOUNT)
        req = mock_open.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer my-token"


# ── refresh_access_token ──────────────────────────────────────────────────────


class TestRefreshAccessToken:
    def test_returns_access_token_on_success(self):
        response = _mock_response({"access_token": "new-token", "expires_in": 3600})
        with patch("gera.service.google_calendar.urllib.request.urlopen", return_value=response):
            result = refresh_access_token("my-refresh-token")
        assert result["access_token"] == "new-token"

    def test_http_error_raises_value_error(self):
        import urllib.error

        err = urllib.error.HTTPError(
            url="https://example.com",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=BytesIO(b"invalid_grant"),
        )
        with patch("gera.service.google_calendar.urllib.request.urlopen", side_effect=err):
            with pytest.raises(ValueError, match="400"):
                refresh_access_token("expired-token")


# ── sync_google_events (deduplication logic) ──────────────────────────────────


class TestSyncGoogleEvents:
    def _patch_fetch(self, raw_events: list[dict]):
        """Context manager that stubs fetch_google_events to return raw_events."""
        return patch(
            "gera.service.google_calendar.fetch_google_events",
            return_value=raw_events,
        )

    def test_new_event_is_created(self, repo: Repository):
        raw = [_gcal_event(id="new-1", summary="New Event")]
        with self._patch_fetch(raw):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        assert result.created == 1
        assert result.updated == 0
        assert result.skipped == 0
        events = repo.list_events()
        assert any("new-1" in e.id for e in events)

    def test_unchanged_event_is_skipped(self, repo: Repository):
        # Pre-populate repo with an event that matches the incoming etag
        repo.create_event(_local_event(id="gcal-user_example.com-gcal-123", etag='"etag-abc"'))
        raw = [_gcal_event(id="gcal-123", etag='"etag-abc"')]
        with self._patch_fetch(raw):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        assert result.skipped == 1
        assert result.created == 0
        assert result.updated == 0

    def test_changed_etag_triggers_update(self, repo: Repository):
        existing_id = f"gcal-{ACCOUNT.replace('@', '_')}-gcal-123"
        repo.create_event(_local_event(id=existing_id, etag='"old-etag"'))
        raw = [_gcal_event(id="gcal-123", etag='"new-etag"')]
        with self._patch_fetch(raw):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        assert result.updated == 1
        assert result.created == 0
        # Confirm etag was updated in repo
        evt = repo.get_event(existing_id)
        assert evt.metadata.etag == '"new-etag"'

    def test_event_not_in_fetch_counted_as_stale(self, repo: Repository):
        # An event in the repo from this account that doesn't appear in the fetch
        repo.create_event(_local_event(id="gcal-user_example.com-old-evt", source_event_id="old-evt"))
        raw = []  # fetch returns nothing
        with self._patch_fetch(raw):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        assert result.stale == 1

    def test_events_from_other_accounts_not_touched(self, repo: Repository):
        # Event from a different account — should not be considered stale
        other_evt = EventEntity(
            id="gcal-other_example.com-x1",
            source="google_calendar",
            from_=datetime(2026, 3, 14, 9, 0),
            to=datetime(2026, 3, 14, 9, 30),
            name="Other account event",
            description="",
            participants=[],
            location="",
            metadata=EventMetadata(
                source_platform="google_calendar",
                source_account="other@example.com",
                source_event_id="x1",
                source_calendar_id=CALENDAR,
            ),
        )
        repo.create_event(other_evt)
        with self._patch_fetch([]):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        # The other account's event should not count as stale for this sync
        assert result.stale == 0
        assert repo.get_event("gcal-other_example.com-x1") is not None

    def test_sync_result_model(self):
        r = SyncResult(created=1, updated=2, skipped=3, stale=4)
        assert r.created == 1
        assert r.updated == 2
        assert r.skipped == 3
        assert r.stale == 4

    def test_multiple_new_events(self, repo: Repository):
        raw = [_gcal_event(id=f"e{i}", summary=f"Event {i}") for i in range(5)]
        with self._patch_fetch(raw):
            result = sync_google_events(repo, "token", ACCOUNT, CALENDAR)
        assert result.created == 5
        assert len(repo.list_events()) == 5
