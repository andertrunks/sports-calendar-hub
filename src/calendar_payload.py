"""Build the privacy-safe contract sent to the Apps Script calendar gateway."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .models import SportsEvent
from .normalize import canonical_event_key, normalize_for_comparison, permanent_uid

SCHEMA_VERSION = "2.0"
MANAGED_BY = "sports-calendar-hub"

RELEVANT_FIELDS = (
    "title", "sport", "category", "age_group", "gender", "competition", "phase",
    "round", "participant_1", "participant_2", "start", "end", "timezone", "all_day",
    "location", "city", "state", "country", "broadcaster_br", "status", "source_url",
    "source_name", "color_group", "color_id", "transparency", "highlight_reason",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def data_hash(events: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json(events).encode("utf-8")).hexdigest()


def semantic_fingerprint(event: SportsEvent) -> str:
    payload: dict[str, Any] = {}
    for field in RELEVANT_FIELDS:
        value = getattr(event, field)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, str):
            value = normalize_for_comparison(value)
        payload[field] = value
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _history_indexes(events: Iterable[SportsEvent]) -> tuple[dict[str, SportsEvent], dict[str, SportsEvent], dict[str, SportsEvent]]:
    by_uid: dict[str, SportsEvent] = {}
    by_external: dict[str, SportsEvent] = {}
    by_canonical: dict[str, SportsEvent] = {}
    for event in events:
        by_uid[permanent_uid(event)] = event
        external = event.external_id_hash or event.external_id
        if external:
            by_external[external] = event
        by_canonical[canonical_event_key(event)] = event
    return by_uid, by_external, by_canonical


def preserve_uid_and_sequence(
    incoming: Iterable[SportsEvent], existing: Iterable[SportsEvent]
) -> tuple[list[SportsEvent], dict[str, int]]:
    """Preserve identity and increment sequence only for a real sports-data change."""

    by_uid, by_external, by_canonical = _history_indexes(existing)
    result: list[SportsEvent] = []
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    now = datetime.now(UTC)
    for event in incoming:
        candidate_uid = permanent_uid(event)
        previous = by_external.get(event.external_id_hash or event.external_id)
        previous = previous or by_uid.get(candidate_uid) or by_canonical.get(canonical_event_key(event))
        if previous is None:
            uid = candidate_uid
            sequence = max(0, event.sequence)
            created_at = event.created_at or event.last_verified or now
            last_modified = event.last_modified or event.last_verified or now
            counts["created"] += 1
        else:
            uid = permanent_uid(previous)
            created_at = previous.created_at or previous.last_verified or now
            if semantic_fingerprint(previous) == semantic_fingerprint(event):
                sequence = previous.sequence
                last_modified = previous.last_modified or previous.last_verified or now
                counts["unchanged"] += 1
            else:
                sequence = max(previous.sequence + 1, event.sequence)
                last_modified = event.last_verified or now
                counts["updated"] += 1
        result.append(
            replace(
                event,
                uid=uid,
                external_id_hash=event.external_id_hash or event.external_id,
                created_at=created_at,
                last_modified=last_modified,
                sequence=sequence,
                managed_by=MANAGED_BY,
                scope_version=SCHEMA_VERSION,
                transparency="TRANSPARENT",
            )
        )
    return result, counts


def event_to_gateway(event: SportsEvent) -> dict[str, Any]:
    uid = permanent_uid(event)
    if not uid.endswith("@sports-calendar-hub"):
        raise ValueError("UID fora do domínio permanente")
    zone = ZoneInfo(event.timezone)
    start = event.start.astimezone(zone).isoformat()
    end = event.end.astimezone(zone).isoformat() if event.end else None
    if event.all_day:
        start = event.start.date().isoformat()
        end_date = event.end.date() if event.end else event.start.date() + timedelta(days=1)
        if end_date <= event.start.date():
            end_date = event.start.date() + timedelta(days=1)
        end = end_date.isoformat()
    return {
        "uid": uid,
        "external_id_hash": event.external_id_hash or event.external_id,
        "title": event.title,
        "sport": event.sport,
        "category": event.category,
        "age_group": event.age_group,
        "gender": event.gender,
        "competition": event.competition,
        "phase": event.phase,
        "round": event.round,
        "participant_1": event.participant_1,
        "participant_2": event.participant_2,
        "start": start,
        "end": end,
        "timezone": event.timezone,
        "all_day": event.all_day,
        "location": event.location,
        "city": event.city,
        "state": event.state,
        "country": event.country,
        "broadcaster_br": event.broadcaster_br,
        "status": event.status,
        "source_url": event.source_url,
        "source_name": event.source_name,
        "color_group": event.color_group,
        "color_id": event.color_id,
        "transparency": "TRANSPARENT",
        "sequence": event.sequence,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "last_modified": event.last_modified.isoformat() if event.last_modified else None,
        "last_verified": event.last_verified.isoformat() if event.last_verified else None,
        "highlight_reason": event.highlight_reason,
        "managed_by": MANAGED_BY,
        "scope_version": SCHEMA_VERSION,
    }


def build_sync_payload(events: Iterable[SportsEvent], *, dry_run: bool) -> dict[str, Any]:
    serialized = [event_to_gateway(event) for event in events]
    return {
        "action": "sync",
        "dry_run": dry_run,
        "schema_version": SCHEMA_VERSION,
        "source_hash": data_hash(serialized),
        "events": serialized,
    }
