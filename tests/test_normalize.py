from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from src.normalize import (
    assign_color_group,
    clean_display_text,
    normalize_for_comparison,
    normalize_participant,
    permanent_uid,
    split_matchup,
)
from tests import make_event


def test_normalizacao_de_acentos() -> None:
    assert normalize_for_comparison("  São   PÁULO  ") == "sao paulo"


def test_normalizacao_de_espacos_e_html() -> None:
    assert clean_display_text(" <b>Arsenal</b>   x\n Liverpool ") == "Arsenal x Liverpool"


@pytest.mark.parametrize("separator", ["x", "vs", "versus", "×"])
def test_separadores_de_confronto(separator: str) -> None:
    assert split_matchup(f"Equipe A {separator} Equipe B") == ("Equipe A", "Equipe B")


def test_normalizacao_de_participante_preserva_alias() -> None:
    assert normalize_participant("São Paulo Futebol Clube") == "sao paulo"


def test_geracao_de_uid_estavel() -> None:
    event = make_event()
    assert permanent_uid(event) == permanent_uid(event)
    assert permanent_uid(event).endswith("@sports-calendar-hub")


def test_uid_permanece_igual_apos_mudanca_de_horario() -> None:
    event = make_event()
    moved = replace(event, start=event.start + timedelta(days=2), end=event.end + timedelta(days=2))
    assert permanent_uid(event) == permanent_uid(moved)


def test_uid_sem_external_id_nao_depende_do_horario() -> None:
    event = make_event(external_id="")
    moved = replace(event, start=event.start + timedelta(hours=5), end=event.end + timedelta(hours=5))
    assert permanent_uid(event) == permanent_uid(moved)


def test_prioridade_sao_paulo_sobre_brasileirao() -> None:
    event = make_event(participant_1="São Paulo", competition="Brasileirão")
    assert assign_color_group(event) == "sao-paulo"


def test_prioridade_brasil_sobre_copa_do_mundo() -> None:
    event = make_event(participant_1="Brasil", competition="Copa do Mundo")
    assert assign_color_group(event) == "selecao-brasileira"


def test_prioridade_red_bull_sobre_competicao_continental() -> None:
    event = make_event(participant_1="RB Leipzig", competition="Champions League")
    assert assign_color_group(event) == "red-bull"


def test_modelo_rejeita_status_invalido() -> None:
    with pytest.raises(ValueError, match="status inválido"):
        make_event(status="UNKNOWN")


def test_modelo_rejeita_termino_antes_do_inicio() -> None:
    event = make_event()
    with pytest.raises(ValueError, match="posterior"):
        make_event(end=event.start - timedelta(minutes=1))
