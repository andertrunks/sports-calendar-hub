from __future__ import annotations

from dataclasses import replace

from src.calendar_payload import build_sync_payload, event_to_gateway
from src.normalize import permanent_uid
from tests import make_event


def test_payload_tem_uid_cor_transparencia_e_sem_dados_privados() -> None:
    event = make_event(participant_1="São Paulo", participant_2="Palmeiras")
    payload = event_to_gateway(event)
    assert payload["uid"].endswith("@sports-calendar-hub")
    assert payload["color_id"] in {"8", "11"}
    assert payload["transparency"] == "TRANSPARENT"
    assert "attendees" not in payload
    assert "conferenceData" not in payload


def test_uid_permanece_quando_horario_muda() -> None:
    event = make_event(external_id="hash-estavel")
    moved = replace(event, start=event.start.replace(hour=22), end=event.end.replace(hour=23))
    assert permanent_uid(event) == permanent_uid(moved)


def test_payload_dry_run_tem_hash_deterministico() -> None:
    event = make_event(external_id="hash-estavel")
    first = build_sync_payload([event], dry_run=True)
    second = build_sync_payload([event], dry_run=True)
    assert first["source_hash"] == second["source_hash"]
    assert first["dry_run"] is True


def test_evento_dia_inteiro_nao_inventa_meia_noite_visivel() -> None:
    event = make_event(all_day=True)
    payload = event_to_gateway(event)
    assert len(payload["start"]) == 10
    assert len(payload["end"]) == 10
