"""Load, normalize, deduplicate and publish all feeds."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, DOCS_DIR
from .deduplicate import deduplicate_events
from .ics_generator import generate_calendars, generate_index
from .models import SportsEvent
from .normalize import normalize_event
from .scope_rules import is_event_in_scope, load_scope_rules


def load_events(path: Path = DATA_DIR / "events.json") -> list[SportsEvent]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_events = payload["events"] if isinstance(payload, dict) else payload
    return [SportsEvent.from_dict(item) for item in raw_events]


def run() -> dict[str, int]:
    normalized = [normalize_event(event) for event in load_events()]
    in_scope = [event for event in normalized if is_event_in_scope(event)]
    events = deduplicate_events(in_scope)
    generated_at = (
        max(event.last_verified for event in events)
        if events
        else datetime.fromisoformat(load_scope_rules()["updated_at"])
    )
    counts, changed = generate_calendars(events, DOCS_DIR)
    index_changed = generate_index(counts, generated_at, DOCS_DIR)
    print(
        json.dumps(
            {
                "input_events": len(normalized),
                "in_scope_events": len(in_scope),
                "unique_events": len(events),
                "feeds": counts,
                "changed_files": len(changed) + int(index_changed),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return counts


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
