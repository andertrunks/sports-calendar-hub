"""Create a sanitized, UID-based change history for generated data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from .calendar_payload import semantic_fingerprint
from .models import SportsEvent
from .normalize import permanent_uid


def compare_events(old: Iterable[SportsEvent], new: Iterable[SportsEvent]) -> dict[str, Any]:
    old_map = {permanent_uid(event): event for event in old}
    new_map = {permanent_uid(event): event for event in new}
    created = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    updated = sorted(
        uid for uid in set(old_map) & set(new_map)
        if semantic_fingerprint(old_map[uid]) != semantic_fingerprint(new_map[uid])
    )
    unchanged = len(set(old_map) & set(new_map)) - len(updated)
    return {
        "created_uids": created,
        "updated_uids": updated,
        "removed_uids": removed,
        "counts": {
            "created": len(created),
            "updated": len(updated),
            "removed": len(removed),
            "unchanged": unchanged,
        },
    }
