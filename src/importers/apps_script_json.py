"""Import and validate the sanitized Apps Script gateway export."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dateutil.parser import isoparse

from ..calendar_payload import SCHEMA_VERSION, data_hash, preserve_uid_and_sequence
from ..config import DATA_DIR, DEFAULT_TIMEZONE, PROJECT_ROOT
from ..deduplicate import deduplicate_events
from ..models import SportsEvent
from ..normalize import normalize_event, permanent_uid
from ..scope_rules import determine_priority, is_event_in_scope

FORBIDDEN_EXPORT_FIELDS = {
    "email", "organizer", "creator", "attendees", "conferenceData", "conference_data",
    "meet", "calendar_id", "event_id", "raw_id", "edit_link", "response_link", "token",
}


def load_export(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_export(payload)
    return payload


def validate_export(payload: dict[str, Any]) -> None:
    if payload.get("ok") is not True:
        raise ValueError("exportação do gateway não confirmou ok=true")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema_version incompatível")
    if payload.get("timezone") != DEFAULT_TIMEZONE:
        raise ValueError("fuso de exportação incompatível")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("events deve ser uma lista")
    if payload.get("event_count") != len(events):
        raise ValueError("event_count não corresponde a events")
    if payload.get("data_hash") != data_hash(events):
        raise ValueError("data_hash inválido")
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"events[{index}] não é objeto")
        forbidden = FORBIDDEN_EXPORT_FIELDS & set(event)
        if forbidden:
            raise ValueError(f"events[{index}] contém campos proibidos: {sorted(forbidden)}")
        text = json.dumps(event, ensure_ascii=False).casefold()
        if "meet.google.com" in text or "calendar.google.com" in text or "@gmail.com" in text:
            raise ValueError(f"events[{index}] contém conteúdo privado")


def _event_from_export(raw: dict[str, Any]) -> SportsEvent:
    timezone = str(raw.get("timezone") or DEFAULT_TIMEZONE)
    zone = ZoneInfo(timezone)
    all_day = bool(raw.get("all_day", False))
    raw_start = str(raw.get("start") or "")
    if not raw_start:
        raise ValueError("start ausente")
    if all_day:
        start = datetime.fromisoformat(raw_start[:10]).replace(tzinfo=zone)
        raw_end = str(raw.get("end") or "")
        end = (
            datetime.fromisoformat(raw_end[:10]).replace(tzinfo=zone)
            if raw_end
            else start + timedelta(days=1)
        )
    else:
        start = isoparse(raw_start)
        if start.tzinfo is None:
            start = start.replace(tzinfo=zone)
        raw_end = str(raw.get("end") or "")
        end = isoparse(raw_end) if raw_end else start + timedelta(hours=2, minutes=30)
        if end.tzinfo is None:
            end = end.replace(tzinfo=zone)
    verified_raw = raw.get("last_verified") or raw.get("generated_at")
    verified = isoparse(str(verified_raw)) if verified_raw else start.astimezone(UTC)
    if verified.tzinfo is None:
        verified = verified.replace(tzinfo=zone)
    event = SportsEvent(
        uid=str(raw.get("uid") or ""),
        source_id="sports-calendar-hub-gateway",
        source_name=str(raw.get("source_name") or "Controle de Eventos Esportivos — aba Eventos"),
        external_id=str(raw.get("external_id_hash") or ""),
        external_id_hash=str(raw.get("external_id_hash") or ""),
        title=str(raw.get("title") or ""),
        sport=str(raw.get("sport") or ""),
        category=str(raw.get("category") or ""),
        age_group=str(raw.get("age_group") or ""),
        gender=str(raw.get("gender") or ""),
        competition=str(raw.get("competition") or ""),
        phase=str(raw.get("phase") or ""),
        round=str(raw.get("round") or ""),
        participant_1=str(raw.get("participant_1") or ""),
        participant_2=str(raw.get("participant_2") or ""),
        start=start,
        end=end,
        timezone=timezone,
        all_day=all_day,
        location=str(raw.get("location") or ""),
        city=str(raw.get("city") or ""),
        state=str(raw.get("state") or ""),
        country=str(raw.get("country") or ""),
        broadcaster_br=str(raw.get("broadcaster_br") or ""),
        status=str(raw.get("status") or "CONFIRMED"),
        source_url=str(raw.get("source_url") or ""),
        color_group=str(raw.get("color_group") or "outros-esportes"),
        color_id=str(raw.get("color_id") or "8"),
        transparency="TRANSPARENT",
        priority=int(raw.get("priority") or 0),
        last_verified=verified,
        highlight_reason=str(raw.get("highlight_reason") or ""),
        sequence=int(raw.get("sequence") or 0),
    )
    event = normalize_event(event)
    event.priority = determine_priority(event)
    return event


def _read_existing(path: Path) -> list[SportsEvent]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("events", payload) if isinstance(payload, dict) else payload
    return [SportsEvent.from_dict(row) for row in rows]


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def import_export(
    payload: dict[str, Any], events_path: Path = DATA_DIR / "events.json"
) -> tuple[list[SportsEvent], dict[str, Any]]:
    validate_export(payload)
    converted: list[SportsEvent] = []
    rejected: list[str] = []
    for index, raw in enumerate(payload["events"]):
        try:
            event = _event_from_export(raw)
        except (TypeError, ValueError) as exc:
            rejected.append(f"linha {index + 1}: {exc}")
            continue
        if is_event_in_scope(event):
            converted.append(event)
    unique = deduplicate_events(converted)
    preserved, changes = preserve_uid_and_sequence(unique, _read_existing(events_path))
    preserved.sort(key=lambda event: (event.start, event.title, permanent_uid(event)))
    document = {
        "schema_version": SCHEMA_VERSION,
        "snapshot": {
            "source": "Sports Calendar Hub Gateway",
            "sheet": "Eventos",
            "source_hash": payload["data_hash"],
            "imported_at": payload["generated_at"],
            "privacy": "IDs de origem somente como hashes SHA-256; sem credenciais ou participantes.",
        },
        "events": [event.to_dict() for event in preserved],
    }
    changed = _write_json_if_changed(events_path, document)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_rows": len(payload["events"]),
        "in_scope": len(converted),
        "unique_events": len(preserved),
        "deduplicated": len(converted) - len(unique),
        "rejected": rejected,
        "changes": changes,
        "events_json_changed": changed,
        "source_hash": payload["data_hash"],
    }
    return preserved, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--events-path", type=Path, default=DATA_DIR / "events.json")
    args = parser.parse_args()
    _, summary = import_export(load_export(args.json_path), args.events_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
