from __future__ import annotations

from pathlib import Path

from src.calendar_payload import data_hash
from src.importers.apps_script_json import load_export


def test_fixture_remota_representa_exportacao_sanitizada() -> None:
    path = Path(__file__).parent / "fixtures" / "apps_script_export.json"
    payload = load_export(path)
    assert payload["data_hash"] == data_hash(payload["events"])
    assert all("external_id_hash" in event for event in payload["events"])
