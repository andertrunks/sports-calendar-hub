"""Import a temporary CSV export of the Google Sheet tab named ``Eventos``."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.parser import parse as parse_datetime

from ..config import DATA_DIR, DEFAULT_TIMEZONE, PROJECT_ROOT
from ..deduplicate import deduplicate_events
from ..models import SportsEvent
from ..normalize import clean_display_text, normalize_event, normalize_for_comparison
from ..scope_rules import (
    determine_color_group,
    determine_priority,
    identify_age_category,
    identify_competition,
    identify_team,
    is_copinha_event_allowed,
    is_event_in_scope,
    is_excluded_sao_paulo_female_youth,
    load_scope_rules,
)

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PRIVATE_URL = re.compile(
    r"https?://(?:calendar\.google\.com|group\.calendar\.google\.com|meet\.google\.com|(?:www\.)?zoom\.us)\S*",
    re.IGNORECASE,
)
_FORBIDDEN_HOSTS = {
    "calendar.google.com",
    "group.calendar.google.com",
    "meet.google.com",
    "zoom.us",
    "www.zoom.us",
}


def _header_key(value: str) -> str:
    return normalize_for_comparison(value).replace(" ", "_")


def _row_values(row: dict[str, str]) -> dict[str, str]:
    return {_header_key(key): str(value or "").strip() for key, value in row.items() if key is not None}


def _value(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(_header_key(name), "")
        if value:
            return value
    return ""


def sanitize_public_text(value: str) -> str:
    cleaned = clean_display_text(value)
    cleaned = _EMAIL.sub("", cleaned)
    cleaned = _PRIVATE_URL.sub("", cleaned)
    cleaned = re.sub(r"\bGoogle Meet\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\battendees?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\borganizer\b", "", cleaned, flags=re.IGNORECASE)
    return clean_display_text(cleaned)


def sanitize_public_url(value: str) -> str:
    candidate = clean_display_text(value)
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    hostname = (parsed.hostname or "").casefold()
    if hostname in _FORBIDDEN_HOSTS:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def hash_external_id(original_id: str, synchronization_key: str = "") -> str:
    if original_id.strip():
        identity = "google-calendar:" + original_id.strip()
    elif synchronization_key.strip():
        identity = "google-sheet-sync:" + synchronization_key.strip()
    else:
        return ""
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _parse_date(value: str) -> datetime.date:
    if not value.strip():
        raise ValueError("data ausente")
    return parse_datetime(value, dayfirst=True, fuzzy=False).date()


def _parse_time(value: str) -> time | None:
    if not value.strip():
        return None
    return parse_datetime(value, dayfirst=True, fuzzy=False).time().replace(second=0, microsecond=0)


def _parse_verified(value: str, zone: ZoneInfo, fallback: datetime) -> datetime:
    if not value.strip():
        return fallback
    parsed = parse_datetime(value, dayfirst=True, fuzzy=False)
    return parsed.replace(tzinfo=zone) if parsed.tzinfo is None else parsed.astimezone(zone)


def _status(value: str) -> str:
    normalized = normalize_for_comparison(value)
    if any(term in normalized for term in ("cancelado", "cancelled")):
        return "CANCELLED"
    if any(term in normalized for term in ("adiado", "postponed")):
        return "POSTPONED"
    if any(term in normalized for term in ("tentative", "provisorio", "horario a confirmar")):
        return "TENTATIVE"
    return "CONFIRMED"


def _default_duration(sport: str) -> timedelta:
    normalized = normalize_for_comparison(sport)
    if "automobilismo" in normalized:
        return timedelta(hours=1)
    if "tenis" in normalized:
        return timedelta(hours=2)
    return timedelta(hours=2, minutes=30)


def _make_title(participant_1: str, participant_2: str, competition: str, phase: str) -> str:
    matchup = " x ".join(value for value in (participant_1, participant_2) if value)
    pieces = [value for value in (matchup, competition, phase) if value]
    return " | ".join(pieces)


def _event_from_row(row: dict[str, str]) -> tuple[SportsEvent, list[str]]:
    timezone_name = _value(row, "Fuso horário", "Fuso") or DEFAULT_TIMEZONE
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone_name = DEFAULT_TIMEZONE
        zone = ZoneInfo(DEFAULT_TIMEZONE)

    sport = sanitize_public_text(_value(row, "Modalidade"))
    category = sanitize_public_text(_value(row, "Categoria"))
    participant_1 = sanitize_public_text(_value(row, "Participante 1"))
    participant_2 = sanitize_public_text(_value(row, "Participante 2"))
    competition = sanitize_public_text(_value(row, "Competição"))
    phase = sanitize_public_text(_value(row, "Fase ou rodada", "Fase", "Rodada"))
    title = sanitize_public_text(_value(row, "Título")) or _make_title(
        participant_1, participant_2, competition, phase
    )
    if not title or not (participant_1 or participant_2 or competition):
        raise ValueError("evento não identificável")

    event_date = _parse_date(_value(row, "Data"))
    start_time = _parse_time(_value(row, "Hora de início", "Início"))
    end_time = _parse_time(_value(row, "Hora de término", "Término"))
    incomplete: list[str] = []
    if start_time is None:
        start = datetime.combine(event_date, time.min, tzinfo=zone)
        end = start + timedelta(days=1)
        all_day = True
        incomplete.append("horário")
    else:
        start = datetime.combine(event_date, start_time, tzinfo=zone)
        all_day = False
        if end_time is None:
            end = start + _default_duration(sport)
            incomplete.append("hora de término")
        else:
            end = datetime.combine(event_date, end_time, tzinfo=zone)
            if end <= start:
                end += timedelta(days=1)

    broadcaster = sanitize_public_text(_value(row, "Transmissão no Brasil", "Transmissão"))
    source_url = sanitize_public_url(_value(row, "Fonte oficial", "Fonte"))
    if not broadcaster:
        incomplete.append("transmissão")
    if not source_url:
        incomplete.append("fonte")
    if not competition:
        incomplete.append("competição")

    external_id = hash_external_id(
        _value(row, "ID do evento"), _value(row, "Chave de sincronização")
    )
    last_verified = _parse_verified(_value(row, "Última verificação"), zone, start)

    event = SportsEvent(
        source_id="control-sheet-events-snapshot",
        source_name="Controle de Eventos Esportivos — aba Eventos",
        external_id=external_id,
        title=title,
        sport=sport,
        category=category,
        competition=competition,
        phase=phase,
        participant_1=participant_1,
        participant_2=participant_2,
        start=start,
        end=end,
        timezone=timezone_name,
        all_day=all_day,
        location=sanitize_public_text(_value(row, "Local")),
        city=sanitize_public_text(_value(row, "Cidade")),
        country=sanitize_public_text(_value(row, "País")),
        broadcaster_br=broadcaster,
        status=_status(_value(row, "Status")),
        source_url=source_url,
        color_group="outros-esportes",
        priority=0,
        last_verified=last_verified,
        sequence=0,
    )
    event = normalize_event(event)
    event.priority = determine_priority(event)
    event.color_group = determine_color_group(event)
    return event, sorted(set(incomplete))


def _write_json_if_changed(path: Path, payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Relatório de importação",
        "",
        f"- Importação: {summary['imported_at']}",
        f"- Linhas lidas: {summary['total_rows_read']}",
        f"- Eventos importados: {summary['total_imported']}",
        f"- Duplicatas consolidadas: {summary['total_deduplicated']}",
        f"- Eventos excluídos: {summary['total_excluded']}",
        f"- Eventos pendentes: {summary['total_pending']}",
        f"- Sem transmissão: {summary['events_without_transmission']}",
        f"- Sem fonte: {summary['events_without_source']}",
        f"- Incompletos importados: {summary['incomplete_events']}",
        f"- São Paulo feminino de base excluídos: {summary['sao_paulo_female_youth_excluded']}",
        f"- Botafogo-SP importados: {summary['botafogo_sp_imported']}",
        f"- Comercial-SP importados: {summary['comercial_sp_imported']}",
        f"- Copinha importados: {summary['copinha_imported']}",
        f"- Copinha ignorados por fase: {summary['copinha_ignored_by_phase']}",
        "",
        "## Classificação das linhas",
        "",
    ]
    for name, count in summary["classification_counts"].items():
        lines.append(f"- {name}: {count}")
    for heading, key in (
        ("Quantidade por grupo", "by_group"),
        ("Quantidade por modalidade", "by_sport"),
        ("Quantidade por competição", "by_competition"),
    ):
        lines.extend(("", f"## {heading}", ""))
        for name, count in summary[key].items():
            lines.append(f"- {name}: {count}")
    lines.extend(("", "## Avisos", ""))
    lines.extend(f"- {warning}" for warning in summary["warnings"])
    if summary["conversion_errors"]:
        lines.extend(("", "## Erros de conversão", ""))
        lines.extend(f"- {error}" for error in summary["conversion_errors"])
    return "\n".join(lines) + "\n"


def import_csv(
    csv_path: Path,
    events_path: Path = DATA_DIR / "events.json",
    reports_dir: Path = PROJECT_ROOT / "reports",
) -> dict[str, Any]:
    rules = load_scope_rules()
    classification: Counter[str] = Counter()
    accepted: list[SportsEvent] = []
    incomplete_by_external: dict[str, list[str]] = {}
    conversion_errors: list[str] = []
    female_youth = Counter()
    copinha_ignored = 0

    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV sem cabeçalho")
        rows = list(reader)

    for row_number, raw_row in enumerate(rows, start=2):
        row = _row_values(raw_row)
        try:
            event, incomplete = _event_from_row(row)
        except ValueError as exc:
            message = str(exc)
            if "data ausente" in message or "não identificável" in message:
                classification["PENDENTE_INCOMPLETO"] += 1
            else:
                classification["EXCLUÍDO_INVÁLIDO"] += 1
            conversion_errors.append(f"linha {row_number}: {message}")
            continue

        if is_excluded_sao_paulo_female_youth(event, rules):
            classification["EXCLUÍDO_SÃO_PAULO_FEMININO_BASE"] += 1
            category = identify_age_category(event.category)
            if category == "female-u17":
                female_youth["sub17"] += 1
            elif category == "female-u20":
                female_youth["sub20"] += 1
            else:
                female_youth["other"] += 1
            continue

        if not is_event_in_scope(event, rules):
            classification["EXCLUÍDO_FORA_DO_ESCOPO"] += 1
            if identify_competition(event.competition, rules) == "copinha" and not is_copinha_event_allowed(
                event, rules
            ):
                copinha_ignored += 1
            continue

        classification["IMPORTADO"] += 1
        accepted.append(event)
        if incomplete:
            incomplete_by_external[event.external_id] = incomplete

    unique = deduplicate_events(accepted)
    duplicate_count = len(accepted) - len(unique)
    if duplicate_count:
        classification["IMPORTADO"] -= duplicate_count
        classification["EXCLUÍDO_DUPLICATA"] += duplicate_count

    unique_external = {event.external_id for event in unique}
    incomplete_count = sum(1 for external in incomplete_by_external if external in unique_external)
    imported_at = max(
        (event.last_verified for event in unique),
        default=datetime.fromisoformat(rules["updated_at"]),
    ).astimezone(ZoneInfo(DEFAULT_TIMEZONE))

    events_payload = {
        "schema_version": "1.0.0",
        "snapshot": {
            "source": "Controle de Eventos Esportivos",
            "sheet": "Eventos",
            "imported_at": imported_at.isoformat(),
            "privacy": "IDs originais removidos; somente hashes SHA-256 são armazenados.",
        },
        "events": [event.to_dict() for event in unique],
    }
    events_changed = _write_json_if_changed(events_path, events_payload)

    groups = Counter(event.color_group for event in unique)
    sports = Counter(event.sport or "(não informado)" for event in unique)
    competitions = Counter(event.competition or "(não informada)" for event in unique)
    team_ids = [
        (identify_team(event.participant_1, rules), identify_team(event.participant_2, rules))
        for event in unique
    ]
    warnings: list[str] = []
    if not any("botafogo-sp" in pair for pair in team_ids):
        warnings.append("Nenhum jogo do Botafogo-SP estava presente no snapshot da aba Eventos.")
    if not any("comercial-sp" in pair for pair in team_ids):
        warnings.append("Nenhum jogo do Comercial-SP estava presente no snapshot da aba Eventos.")
    if not any(identify_competition(event.competition, rules) == "copinha" for event in unique):
        warnings.append("Nenhum jogo da Copinha estava presente no snapshot da aba Eventos.")

    summary = {
        "schema_version": "1.0.0",
        "imported_at": imported_at.isoformat(),
        "total_rows_read": len(rows),
        "total_imported": len(unique),
        "total_after_deduplication": len(unique),
        "total_deduplicated": duplicate_count,
        "total_excluded": sum(
            count for name, count in classification.items() if name.startswith("EXCLUÍDO")
        ),
        "total_pending": classification["PENDENTE_INCOMPLETO"],
        "events_without_transmission": sum(not event.broadcaster_br for event in unique),
        "events_without_source": sum(not event.source_url for event in unique),
        "incomplete_events": incomplete_count,
        "sao_paulo_female_youth_excluded": sum(female_youth.values()),
        "sao_paulo_female_u17_excluded": female_youth["sub17"],
        "sao_paulo_female_u20_excluded": female_youth["sub20"],
        "sao_paulo_other_female_youth_excluded": female_youth["other"],
        "botafogo_sp_imported": sum("botafogo-sp" in pair for pair in team_ids),
        "comercial_sp_imported": sum("comercial-sp" in pair for pair in team_ids),
        "copinha_imported": sum(
            identify_competition(event.competition, rules) == "copinha" for event in unique
        ),
        "copinha_ignored_by_phase": copinha_ignored,
        "classification_counts": dict(sorted(classification.items())),
        "by_group": dict(sorted(groups.items())),
        "by_sport": dict(sorted(sports.items())),
        "by_competition": dict(sorted(competitions.items())),
        "events_json_changed": events_changed,
        "conversion_errors": conversion_errors,
        "warnings": warnings,
    }
    _write_json_if_changed(reports_dir / "import-summary.json", summary)
    markdown = _report_markdown(summary)
    markdown_path = reports_dir / "import-summary.md"
    if not markdown_path.exists() or markdown_path.read_text(encoding="utf-8") != markdown:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV temporário exportado somente da aba Eventos")
    args = parser.parse_args()
    summary = import_csv(args.csv_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

