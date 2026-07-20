from __future__ import annotations

import re
from pathlib import Path

from icalendar import Calendar

from src.config import COLOR_GROUPS, FEED_METADATA, PRODID
from src.ics_generator import build_calendar, generate_calendars, generate_index
from src.normalize import normalize_event, permanent_uid
from src.validate_ics import validate_directory
from tests import make_event


def _events_from(raw: bytes):
    return Calendar.from_ical(raw).walk("VEVENT")


def test_geracao_do_all_ics(tmp_path: Path) -> None:
    event = normalize_event(make_event(participant_1="São Paulo"))
    counts, _ = generate_calendars([event], tmp_path)
    assert (tmp_path / "all.ics").exists()
    assert counts["all"] == 1
    assert len(_events_from((tmp_path / "all.ics").read_bytes())) == 1


def test_geracao_de_todos_os_feeds_separados(tmp_path: Path) -> None:
    event = normalize_event(make_event(participant_1="São Paulo"))
    counts, _ = generate_calendars([event], tmp_path)
    assert {path.stem for path in tmp_path.glob("*.ics")} == set(FEED_METADATA)
    assert counts["sao-paulo"] == 1
    assert sum(counts[group] for group in COLOR_GROUPS) == 1


def test_evento_aparece_no_all_e_em_exatamente_um_grupo(tmp_path: Path) -> None:
    event = normalize_event(make_event(participant_1="Arsenal", competition="Premier League"))
    counts, _ = generate_calendars([event], tmp_path)
    assert counts["all"] == 1
    assert counts["premier-league"] == 1
    assert sum(counts[group] for group in COLOR_GROUPS) == 1


def test_ausencia_de_uid_duplicado() -> None:
    first = normalize_event(make_event(external_id="one"))
    second = normalize_event(make_event(external_id="two", participant_1="Equipe C", participant_2="Equipe D"))
    uids = [str(item["UID"]) for item in _events_from(build_calendar([first, second], "all"))]
    assert len(uids) == len(set(uids))


def test_serializacao_e_leitura_do_ics() -> None:
    event = normalize_event(make_event())
    parsed = Calendar.from_ical(build_calendar([event], "all"))
    assert parsed.name == "VCALENDAR"
    assert str(parsed["PRODID"]) == PRODID
    assert str(parsed["METHOD"]) == "PUBLISH"


def test_evento_cancelado_recebe_status_cancelled() -> None:
    event = normalize_event(make_event(status="CANCELLED"))
    assert str(_events_from(build_calendar([event], "all"))[0]["STATUS"]) == "CANCELLED"


def test_evento_provisorio_recebe_status_tentative() -> None:
    event = normalize_event(make_event(status="TENTATIVE"))
    assert str(_events_from(build_calendar([event], "all"))[0]["STATUS"]) == "TENTATIVE"


def test_evento_adiado_usa_status_ics_valido() -> None:
    event = normalize_event(make_event(status="POSTPONED"))
    component = _events_from(build_calendar([event], "all"))[0]
    assert str(component["STATUS"]) == "TENTATIVE"
    assert "ℹ️ Status: POSTPONED" in str(component["DESCRIPTION"])


def test_uso_de_transp_transparent() -> None:
    event = normalize_event(make_event())
    assert str(_events_from(build_calendar([event], "all"))[0]["TRANSP"]) == "TRANSPARENT"


def test_conteudo_em_utf8() -> None:
    event = normalize_event(
        make_event(
            participant_1="São Paulo",
            title="DADOS DE DEMONSTRAÇÃO — NÃO É CALENDÁRIO OFICIAL — São Paulo x Equipe B",
        )
    )
    raw = build_calendar([event], "all")
    raw.decode("utf-8")
    component = _events_from(raw)[0]
    assert "São Paulo" in str(component["SUMMARY"])
    assert "📺" in str(component["DESCRIPTION"])


def test_quebra_crlf_sem_lf_isolado() -> None:
    raw = build_calendar([normalize_event(make_event())], "all")
    assert raw.endswith(b"\r\n")
    assert re.search(rb"(?<!\r)\n", raw) is None


def test_dobragem_de_linha_longa() -> None:
    event = normalize_event(make_event(title="DADOS DE DEMONSTRAÇÃO — " + "título muito longo " * 20))
    raw = build_calendar([event], "all")
    assert all(len(line) <= 75 for line in raw.split(b"\r\n") if line)
    assert b"\r\n " in raw


def test_validador_aprova_todos_os_feeds(tmp_path: Path) -> None:
    events = [
        normalize_event(make_event(external_id="sp", participant_1="São Paulo")),
        normalize_event(make_event(external_id="tennis", sport="Tênis", participant_1="João", participant_2="Tenista X")),
    ]
    counts, _ = generate_calendars(events, tmp_path)
    generate_index(counts, events[0].last_verified, tmp_path)
    assert validate_directory(tmp_path) == []


def test_uid_publicado_e_o_uid_permanente() -> None:
    event = normalize_event(make_event())
    uid = str(_events_from(build_calendar([event], "all"))[0]["UID"])
    assert uid == permanent_uid(event)
