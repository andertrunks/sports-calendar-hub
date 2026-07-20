from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from src.deduplicate import deduplicate_events
from tests import make_event


def test_deduplicacao_por_external_id() -> None:
    first = make_event()
    changed_time = replace(first, start=first.start + timedelta(days=1), end=first.end + timedelta(days=1))
    assert len(deduplicate_events([first, changed_time])) == 1


def test_deduplicacao_pela_chave_canonica_com_participantes_invertidos() -> None:
    first = make_event(external_id="", source_id="source-a")
    inverted = make_event(
        external_id="",
        source_id="source-b",
        participant_1="Equipe B",
        participant_2="Equipe A",
    )
    assert len(deduplicate_events([first, inverted])) == 1


def test_partidas_diferentes_no_mesmo_horario_permanecem_distintas() -> None:
    first = make_event(external_id="first")
    other = make_event(external_id="other", participant_1="Equipe C", participant_2="Equipe D")
    assert len(deduplicate_events([first, other])) == 2


def test_sao_paulo_x_palmeiras_aparece_uma_vez() -> None:
    first = make_event(
        external_id="",
        source_id="source-a",
        participant_1="São Paulo",
        participant_2="Palmeiras",
        competition="Brasileirão",
    )
    duplicate = make_event(
        external_id="",
        source_id="source-b",
        participant_1="Palmeiras",
        participant_2="São Paulo FC",
        competition="Brasileirão",
    )
    assert len(deduplicate_events([first, duplicate])) == 1


def test_mesmo_jogo_em_duas_fontes_e_consolidado() -> None:
    first = make_event(
        source_id="source-a",
        external_id="",
        broadcaster_br="",
        location="Arena completa",
        priority=100,
    )
    second = make_event(
        source_id="source-b",
        external_id="official-77",
        broadcaster_br="Canal preservado",
        location="",
        priority=80,
    )
    result = deduplicate_events([first, second])
    assert len(result) == 1
    assert result[0].broadcaster_br == "Canal preservado"
    assert result[0].location == "Arena completa"
    assert result[0].external_id == "official-77"


def test_maior_sequence_e_preservado() -> None:
    first = make_event(sequence=1)
    second = replace(first, sequence=7, broadcaster_br="Nova transmissão")
    result = deduplicate_events([first, second])
    assert result[0].sequence == 7


def test_horario_sozinho_nao_cria_duplicata() -> None:
    first = make_event(external_id="one", competition="Competição A")
    second = make_event(
        external_id="two",
        competition="Competição B",
        participant_1="Equipe C",
        participant_2="Equipe D",
    )
    assert first.start == second.start
    assert len(deduplicate_events([first, second])) == 2
