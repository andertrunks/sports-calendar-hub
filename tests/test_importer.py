from __future__ import annotations

import csv
import json
from pathlib import Path

from icalendar import Calendar

from src.ics_generator import generate_calendars, generate_index
from src.importers.google_sheet_csv import import_csv
from src.main import load_events
from src.normalize import permanent_uid

HEADERS = [
    "Chave de sincronização",
    "ID do evento",
    "Título",
    "Modalidade",
    "Categoria",
    "Participante 1",
    "Participante 2",
    "Competição",
    "Fase ou rodada",
    "Data",
    "Hora de início",
    "Hora de término",
    "Fuso horário",
    "Local",
    "Cidade",
    "País",
    "Transmissão no Brasil",
    "Status",
    "ID da cor",
    "Transparência",
    "Fonte oficial",
    "Última verificação",
    "Ação necessária",
    "Sincronizado",
    "Erro",
    "E-mail",
    "attendees",
]


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "Chave de sincronização": "private-sync-key",
        "ID do evento": "raw-google-event-id@google.com",
        "Título": "Futebol — Botafogo-SP x Palmeiras | Copa do Brasil — Quartas",
        "Modalidade": "Futebol",
        "Categoria": "Masculino profissional",
        "Participante 1": "Botafogo-SP",
        "Participante 2": "Palmeiras",
        "Competição": "Copa do Brasil 2026",
        "Fase ou rodada": "Quartas de final",
        "Data": "25/07/2026",
        "Hora de início": "19:30",
        "Hora de término": "22:00",
        "Fuso horário": "America/Sao_Paulo",
        "Local": "Estádio público",
        "Cidade": "Ribeirão Preto",
        "País": "Brasil",
        "Transmissão no Brasil": "ainda não confirmada",
        "Status": "confirmado",
        "ID da cor": "10",
        "Transparência": "TRANSPARENT",
        "Fonte oficial": "https://example.org/evento-publico",
        "Última verificação": "20/07/2026 10:00:00",
        "Ação necessária": "",
        "Sincronizado": "NÃO",
        "Erro": "",
        "E-mail": "pessoa@gmail.com",
        "attendees": "convidado@outlook.com",
    }
    row.update(overrides)
    return row


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def _import(tmp_path: Path, rows: list[dict[str, str]] | None = None):
    csv_path = tmp_path / "eventos.csv"
    events_path = tmp_path / "events.json"
    reports = tmp_path / "reports"
    _write_csv(csv_path, rows or [_row()])
    summary = import_csv(csv_path, events_path=events_path, reports_dir=reports)
    return csv_path, events_path, reports, summary


def test_id_original_google_calendar_nao_aparece_no_events_json(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    text = events_path.read_text(encoding="utf-8")
    assert "raw-google-event-id" not in text
    assert "private-sync-key" not in text


def test_email_nao_aparece_no_events_json(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    text = events_path.read_text(encoding="utf-8")
    assert "@gmail.com" not in text
    assert "@outlook.com" not in text


def test_google_meet_nao_aparece_no_events_json(tmp_path: Path) -> None:
    rows = [_row(**{"Fonte oficial": "https://meet.google.com/abc-defg-hij"})]
    _, events_path, _, _ = _import(tmp_path, rows)
    assert "meet.google.com" not in events_path.read_text(encoding="utf-8")


def test_attendees_nao_aparecem_no_events_json(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    assert "attendees" not in events_path.read_text(encoding="utf-8")


def test_dados_ficticios_nao_aparecem_nos_feeds_de_producao(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    events = load_events(events_path)
    docs = tmp_path / "docs"
    generate_calendars(events, docs)
    assert b"DADOS DE DEMONSTRACAO" not in (docs / "all.ics").read_bytes()
    assert "DADOS DE DEMONSTRAÇÃO" not in (docs / "all.ics").read_text(encoding="utf-8")


def test_csv_bruto_esta_coberto_pelo_gitignore() -> None:
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "data/import/*.csv" in gitignore
    assert "tmp/" in gitignore
    assert "*.tmp" in gitignore


def test_importacao_repetida_gera_o_mesmo_events_json(tmp_path: Path) -> None:
    csv_path, events_path, reports, _ = _import(tmp_path)
    first = events_path.read_bytes()
    import_csv(csv_path, events_path=events_path, reports_dir=reports)
    assert events_path.read_bytes() == first


def test_geracao_repetida_informa_zero_mudancas(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    events = load_events(events_path)
    docs = tmp_path / "docs"
    counts, _ = generate_calendars(events, docs)
    generate_index(counts, events[0].last_verified, docs)
    _, changed = generate_calendars(events, docs)
    index_changed = generate_index(counts, events[0].last_verified, docs)
    assert len(changed) + int(index_changed) == 0


def test_nenhum_uid_duplicado_apos_importacao(tmp_path: Path) -> None:
    rows = [_row(), _row(**{"ID do evento": "raw-google-event-id@google.com"})]
    _, events_path, _, summary = _import(tmp_path, rows)
    events = load_events(events_path)
    uids = [permanent_uid(event) for event in events]
    assert len(uids) == len(set(uids))
    assert summary["total_deduplicated"] == 1


def test_relatorio_nao_contem_dados_pessoais(tmp_path: Path) -> None:
    _, _, reports, _ = _import(tmp_path)
    report_text = (reports / "import-summary.json").read_text(encoding="utf-8")
    assert "@gmail.com" not in report_text
    assert "raw-google-event-id" not in report_text


def test_sao_paulo_feminino_sub17_e_classificado_como_excluido(tmp_path: Path) -> None:
    youth = _row(
        **{
            "ID do evento": "sp-youth",
            "Título": "São Paulo x Ferroviária | Brasileiro Feminino Sub-17",
            "Categoria": "Feminino sub-17",
            "Participante 1": "São Paulo",
            "Participante 2": "Ferroviária",
            "Competição": "Campeonato Brasileiro Feminino Sub-17",
        }
    )
    _, _, _, summary = _import(tmp_path, [youth])
    assert summary["total_imported"] == 0
    assert summary["sao_paulo_female_u17_excluded"] == 1


def test_evento_sem_transmissao_identificavel_e_importado(tmp_path: Path) -> None:
    _, _, _, summary = _import(tmp_path, [_row(**{"Transmissão no Brasil": ""})])
    assert summary["total_imported"] == 1
    assert summary["events_without_transmission"] == 1
    assert summary["incomplete_events"] == 1


def test_status_adiado_e_convertido_para_postponed(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path, [_row(Status="adiado")])
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["events"][0]["status"] == "POSTPONED"


def test_feed_importado_pode_ser_reaberto(tmp_path: Path) -> None:
    _, events_path, _, _ = _import(tmp_path)
    events = load_events(events_path)
    docs = tmp_path / "docs"
    generate_calendars(events, docs)
    assert Calendar.from_ical((docs / "all.ics").read_bytes()).walk("VEVENT")

