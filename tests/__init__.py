"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.models import SportsEvent


def make_event(**overrides: object) -> SportsEvent:
    start = overrides.pop("start", datetime(2026, 8, 1, 16, 0, tzinfo=ZoneInfo("America/Sao_Paulo")))
    defaults: dict[str, object] = {
        "source_id": "source-a",
        "source_name": "Fonte A",
        "external_id": "event-001",
        "title": "DADOS DE DEMONSTRAÇÃO — NÃO É CALENDÁRIO OFICIAL — Equipe A x Equipe B",
        "sport": "Futebol",
        "category": "Futebol masculino",
        "competition": "Competição de demonstração",
        "phase": "Rodada 1",
        "participant_1": "Equipe A",
        "participant_2": "Equipe B",
        "start": start,
        "end": overrides.pop("end", start + timedelta(hours=2)),
        "timezone": "America/Sao_Paulo",
        "all_day": False,
        "location": "Arena fictícia",
        "city": "Cidade fictícia",
        "country": "Brasil",
        "broadcaster_br": "Canal fictício",
        "status": "CONFIRMED",
        "source_url": "",
        "color_group": "outros-esportes",
        "priority": 10,
        "last_verified": datetime(2026, 7, 20, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
        "sequence": 0,
    }
    defaults.update(overrides)
    return SportsEvent(**defaults)
