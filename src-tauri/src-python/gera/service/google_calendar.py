"""Google Calendar sync service.

Fetches events from Google Calendar API and merges them into the local repository
with deduplication based on metadata.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel

from gera.entities import EventEntity, EventMetadata
from gera.repository import Repository

logger = logging.getLogger(__name__)

GCAL_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# Credentials mirrored from src-tauri/src/oauth.rs
_GOOGLE_CLIENT_ID = "690211739966-q4mp5lv90sh42fq0gsban3522k2gfkfp.apps.googleusercontent.com"
_GOOGLE_CLIENT_SECRET = "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"


def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token.

    Args:
        refresh_token: The OAuth refresh token

    Returns:
        Dict with at least ``access_token`` and ``expires_in`` keys

    Raises:
        ValueError: If the refresh request fails
    """
    payload = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": _GOOGLE_CLIENT_ID,
        "client_secret": _GOOGLE_CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data: dict = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise ValueError(f"Token refresh failed ({e.code}): {body}") from e
    logger.debug("Token refreshed successfully; new expires_in=%s", data.get("expires_in"))
    return data


def fetch_google_events(
    access_token: str,
    account_email: str,
    calendar_id: str = "primary",
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
) -> list[dict]:
    """Fetch events from Google Calendar API.

    Returns raw Google Calendar event dicts.
    Uses stdlib urllib to avoid extra dependencies.

    Args:
        access_token: OAuth access token
        account_email: Email address for error reporting
        calendar_id: Google Calendar ID (default 'primary')
        time_min: Start of time window (default -30 days from now)
        time_max: End of time window (default +90 days from now)

    Returns:
        List of raw Google Calendar event dicts
    """
    if time_min is None:
        time_min = datetime.now(timezone.utc) - timedelta(days=30)
    if time_max is None:
        time_max = datetime.now(timezone.utc) + timedelta(days=90)

    logger.info(
        "Fetching Google Calendar events for %s (calendar: %s) from %s to %s",
        account_email,
        calendar_id,
        time_min.isoformat(),
        time_max.isoformat(),
    )

    url = GCAL_EVENTS_URL.format(calendar_id=urllib.parse.quote(calendar_id, safe=""))

    # Format datetimes as RFC3339 with Z suffix (avoids encoding issues with +00:00)
    def _rfc3339(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    base_params = {
        "timeMin": _rfc3339(time_min),
        "timeMax": _rfc3339(time_max),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "2500",
    }

    all_events = []
    page_token = None
    page_num = 1

    while True:
        params = dict(base_params)
        if page_token:
            params["pageToken"] = page_token
        full_url = url + "?" + urllib.parse.urlencode(params)

        try:
            logger.debug("Fetching page %d of events...", page_num)
            req = urllib.request.Request(full_url)
            req.add_header("Authorization", f"Bearer {access_token}")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode(errors="replace")
            logger.error(
                "Failed to fetch Google Calendar events for %s (page %d): %s — %s",
                account_email,
                page_num,
                e,
                error_body,
            )
            raise ValueError(f"Failed to fetch events: {e} — {error_body}") from e

        page_items = data.get("items", [])
        all_events.extend(page_items)
        logger.debug("Page %d: fetched %d events (total: %d)", page_num, len(page_items), len(all_events))

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        page_num += 1

    logger.info(
        "Successfully fetched %d total events from Google Calendar for %s (%d pages)",
        len(all_events),
        account_email,
        page_num,
    )
    return all_events


def _parse_gcal_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse a Google Calendar RFC3339 datetime string.

    Handles both full datetimes and date-only strings.

    Args:
        value: RFC3339 datetime string or date string

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not value:
        return None
    try:
        # Google returns RFC3339: "2026-03-08T14:00:00+01:00" or "2026-03-08" (date only)
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning("Failed to parse datetime: %s", value)
        return None


def google_event_to_entity(
    gcal_event: dict,
    account_email: str,
    calendar_id: str,
) -> Optional[EventEntity]:
    """Convert a Google Calendar event dict to an EventEntity.

    Args:
        gcal_event: Raw Google Calendar event dict
        account_email: Email of the account this came from
        calendar_id: Calendar ID

    Returns:
        EventEntity or None if the event is missing essential date info
    """
    start = gcal_event.get("start", {})
    end = gcal_event.get("end", {})

    # Support both dateTime and date (all-day events)
    from_str = start.get("dateTime") or start.get("date")
    to_str = end.get("dateTime") or end.get("date")
    if not from_str or not to_str:
        logger.debug(
            "Skipping Google Calendar event (missing date): %s - %s",
            gcal_event.get("id"),
            gcal_event.get("summary", "(No title)"),
        )
        return None

    # Stable Gera ID derived from platform + account + source event ID
    source_event_id = gcal_event.get("id", "")
    gera_id = f"gcal-{account_email.replace('@', '_')}-{source_event_id}"
    logger.debug("Converting Google Calendar event to entity: %s", gera_id)

    attendees = gcal_event.get("attendees", [])
    participants = [a.get("email", "") for a in attendees if a.get("email")]

    metadata = EventMetadata(
        source_platform="google_calendar",
        source_account=account_email,
        source_event_id=source_event_id,
        source_calendar_id=calendar_id,
        etag=gcal_event.get("etag", ""),
        last_synced_at=datetime.now(timezone.utc),
        recurring_event_id=gcal_event.get("recurringEventId", ""),
        source_updated_at=_parse_gcal_datetime(gcal_event.get("updated")),
    )

    from_dt = _parse_gcal_datetime(from_str)
    to_dt = _parse_gcal_datetime(to_str)

    if not from_dt or not to_dt:
        logger.warning(
            "Skipping event with unparseable dates: %s - %s (from: %s, to: %s)",
            gcal_event.get("id"),
            gcal_event.get("summary", "(No title)"),
            from_str,
            to_str,
        )
        return None

    logger.debug("Successfully converted: %s", gera_id)
    return EventEntity(
        id=gera_id,
        source="google_calendar",
        from_=from_dt,
        to=to_dt,
        name=gcal_event.get("summary", "(No title)"),
        description=gcal_event.get("description", ""),
        participants=participants,
        location=gcal_event.get("location", ""),
        metadata=metadata,
    )


class SyncResult(BaseModel):
    """Result of a Google Calendar sync operation."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    stale: int = 0  # events in repo but not in fetch (possibly deleted upstream)


def sync_google_events(
    repo: Repository,
    access_token: str,
    account_email: str,
    calendar_id: str = "primary",
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
) -> SyncResult:
    """Fetch events from Google Calendar and merge into the repository.

    Deduplication strategy:
    - Match on source_platform + source_account + source_event_id
    - If match found and etag differs → UPDATE existing event
    - If match found and etag same → SKIP (no changes)
    - If no match → INSERT new event
    - Events not in the fetched set are marked as stale

    Args:
        repo: Repository instance
        access_token: OAuth access token
        account_email: Email address of the account
        calendar_id: Google Calendar ID (default 'primary')
        time_min: Start of sync window (default -30 days)
        time_max: End of sync window (default +90 days)

    Returns:
        SyncResult with counts of created/updated/skipped/stale events
    """
    logger.info(
        "Starting Google Calendar sync for %s (calendar: %s)",
        account_email,
        calendar_id,
    )
    
    raw_events = fetch_google_events(access_token, account_email, calendar_id, time_min, time_max)

    # Convert to entities
    fetched: list[EventEntity] = []
    skipped_conversion = 0
    for raw in raw_events:
        entity = google_event_to_entity(raw, account_email, calendar_id)
        if entity:
            fetched.append(entity)
        else:
            skipped_conversion += 1

    logger.info(
        "Converted %d/%d events to EventEntity format (%d skipped)",
        len(fetched),
        len(raw_events),
        skipped_conversion,
    )

    # Load current events from repo that came from this account
    existing = repo.list_events()
    existing_by_source_id: dict[str, EventEntity] = {}
    for e in existing:
        if (
            e.metadata.source_platform == "google_calendar"
            and e.metadata.source_account == account_email
            and e.metadata.source_calendar_id == calendar_id
        ):
            existing_by_source_id[e.metadata.source_event_id] = e

    logger.info(
        "Found %d existing events from %s (calendar: %s) in repository",
        len(existing_by_source_id),
        account_email,
        calendar_id,
    )

    created = 0
    updated = 0
    skipped = 0

    logger.debug("Starting merge of %d fetched events with %d existing", len(fetched), len(existing_by_source_id))

    for event in fetched:
        source_id = event.metadata.source_event_id
        if source_id in existing_by_source_id:
            old = existing_by_source_id[source_id]
            if old.metadata.etag != event.metadata.etag:
                # ETag differs → event has been updated
                event_with_id = event.model_copy(update={"id": old.id})
                repo.update_event(event_with_id)
                updated += 1
                logger.debug(
                    "Updated event: %s (%s) - old etag: %s, new etag: %s",
                    old.id,
                    event.name,
                    old.metadata.etag[:8],
                    event.metadata.etag[:8],
                )
            else:
                skipped += 1
                logger.debug("Skipped unchanged event: %s (%s)", old.id, event.name)
            # Remove from tracking dict so leftovers = deleted upstream
            del existing_by_source_id[source_id]
        else:
            # New event
            repo.create_event(event)
            created += 1
            logger.debug("Created new event: %s (%s)", event.id, event.name)

    # Events remaining in existing_by_source_id were not in the fetch →
    # they may have been deleted upstream. For safety, mark as stale rather
    # than auto-deleting. (Future: add a `stale` flag or let the user decide.)
    stale = len(existing_by_source_id)
    if stale > 0:
        stale_ids = list(existing_by_source_id.keys())[:5]  # log first 5
        logger.warning(
            "%d events from %s are not in the latest fetch (possibly deleted upstream). "
            "Examples: %s%s",
            stale,
            account_email,
            ", ".join(stale_ids),
            "..." if stale > 5 else "",
        )

    result = SyncResult(created=created, updated=updated, skipped=skipped, stale=stale)
    logger.info(
        "Google Calendar sync complete for %s: created=%d, updated=%d, skipped=%d, stale=%d",
        account_email,
        created,
        updated,
        skipped,
        stale,
    )
    return result
