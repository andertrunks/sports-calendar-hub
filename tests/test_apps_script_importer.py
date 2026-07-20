from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.calendar_payload import data_hash
from src.importers.apps_script_json import import_export, load_export, validate_export
from src.normalize import permanent_uid

FIXTURE = Path(__file__).parent / "fixtures" / "apps_script_export.json"


def test_export_fixture_hash_e_contagem_sao_validos() -> None:
    payload = load_export(FIXTURE)
    assert payload["event_count"] == 2
    assert payload["data_hash"] == data_hash(payload["events"])


def test_importador_preserva_apenas_eventos_no_escopo(tmp_path: Path) -> None:
    events, summary = import_export(load_export(FIXTURE), tmp_path / "events.json")
    assert len(events) == 2
    assert summary["unique_events"] == 2
    assert all(permanent_uid(event).endswith("@sports-calendar-hub") for event in events)


def test_export_com_hash_adulterado_falha() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["events"][0]["title"] += " adulterado"
    with pytest.raises(ValueError, match="data_hash"):
        validate_export(payload)


def test_export_com_attendees_falha() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["events"][0]["attendees"] = ["privado@example.com"]
    payload["data_hash"] = data_hash(payload["events"])
    with pytest.raises(ValueError, match="proibidos"):
        validate_export(payload)
