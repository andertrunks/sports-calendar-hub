"""Build deterministic, credential-free synchronization reports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .models import SportsEvent


def build_report(
    events: Iterable[SportsEvent],
    import_summary: dict[str, Any],
    dry_run_response: dict[str, Any],
    apply_response: dict[str, Any],
) -> dict[str, Any]:
    rows = list(events)
    return {
        "schema_version": "2.0",
        "source_hash": import_summary["source_hash"],
        "events": len(rows),
        "by_group": dict(sorted(Counter(event.color_group for event in rows).items())),
        "import": {k: import_summary[k] for k in ("source_rows", "in_scope", "unique_events", "deduplicated", "changes")},
        "dry_run": {
            "execution_id": dry_run_response.get("execution_id"),
            "plan": dry_run_response.get("plan", {}),
            "primary_duplicate_reviews": len(dry_run_response.get("primary_duplicate_reviews") or []),
        },
        "apply": {
            "execution_id": apply_response.get("execution_id"),
            "plan": apply_response.get("plan", {}),
            "result": apply_response.get("result", {}),
        },
        "security": {
            "calendar": "Eventos esportivos",
            "credentials_persisted": False,
            "attendees_allowed": False,
            "conference_data_allowed": False,
            "primary_calendar_writes": False,
        },
    }


def write_report(path: Path, report: dict[str, Any]) -> bool:
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True
