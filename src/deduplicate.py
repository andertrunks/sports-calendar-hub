"""Multi-stage event deduplication and safe field consolidation."""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import timedelta

from .models import SportsEvent
from .normalize import (
    canonical_event_key,
    canonical_participants,
    normalize_for_comparison,
    permanent_uid,
)

_MERGEABLE_TEXT_FIELDS = (
    "external_id",
    "competition",
    "phase",
    "participant_1",
    "participant_2",
    "location",
    "city",
    "country",
    "broadcaster_br",
    "source_url",
)


def _source_external_key(event: SportsEvent) -> str | None:
    source = normalize_for_comparison(event.source_id or event.source_name)
    external = normalize_for_comparison(event.external_id)
    if source and external:
        return f"{source}|{external}"
    return None


def _completeness(event: SportsEvent) -> int:
    ignored = {"sequence", "priority", "all_day"}
    return sum(
        1
        for item in fields(event)
        if item.name not in ignored and getattr(event, item.name) not in (None, "")
    )


def are_duplicates(left: SportsEvent, right: SportsEvent, tolerance_hours: int = 6) -> bool:
    left_source_external = _source_external_key(left)
    right_source_external = _source_external_key(right)
    if left_source_external and left_source_external == right_source_external:
        return True
    if permanent_uid(left) == permanent_uid(right):
        return True
    if canonical_event_key(left) == canonical_event_key(right):
        return True

    # Time is only an auxiliary signal: participants, sport and competition must also match.
    same_participants = canonical_participants(left) == canonical_participants(right)
    same_sport = normalize_for_comparison(left.sport) == normalize_for_comparison(right.sport)
    same_competition = normalize_for_comparison(left.competition) == normalize_for_comparison(right.competition)
    left_phase = normalize_for_comparison(left.phase)
    right_phase = normalize_for_comparison(right.phase)
    compatible_phase = left_phase == right_phase or not left_phase or not right_phase
    close_in_time = abs(left.start - right.start) <= timedelta(hours=tolerance_hours)
    return bool(
        same_participants
        and same_sport
        and same_competition
        and compatible_phase
        and close_in_time
    )


def merge_events(left: SportsEvent, right: SportsEvent) -> SportsEvent:
    left_score = (_completeness(left), left.priority, left.last_verified)
    right_score = (_completeness(right), right.priority, right.last_verified)
    preferred, alternate = (left, right) if left_score >= right_score else (right, left)
    updates: dict[str, object] = {}
    for field_name in _MERGEABLE_TEXT_FIELDS:
        if not getattr(preferred, field_name) and getattr(alternate, field_name):
            updates[field_name] = getattr(alternate, field_name)
    updates["sequence"] = max(left.sequence, right.sequence)
    updates["priority"] = max(left.priority, right.priority)
    updates["last_verified"] = max(left.last_verified, right.last_verified)
    return replace(preferred, **updates)


def deduplicate_events(events: list[SportsEvent]) -> list[SportsEvent]:
    unique: list[SportsEvent] = []
    for event in events:
        for index, existing in enumerate(unique):
            if are_duplicates(existing, event):
                unique[index] = merge_events(existing, event)
                break
        else:
            unique.append(event)
    return sorted(unique, key=lambda item: (item.start, item.title, permanent_uid(item)))
