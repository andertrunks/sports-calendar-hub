"""Strict structural validation for every generated ICS feed."""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

from icalendar import Calendar

from .config import DOCS_DIR


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    data = path.read_bytes()
    if not data:
        return [f"{path.name}: arquivo vazio"]
    if not data.endswith(b"\r\n"):
        errors.append(f"{path.name}: deve terminar com CRLF")
    if re.search(rb"(?<!\r)\n", data) or re.search(rb"\r(?!\n)", data):
        errors.append(f"{path.name}: contém quebra de linha que não é CRLF")

    physical_lines = data.split(b"\r\n")
    if physical_lines and physical_lines[-1] == b"":
        physical_lines.pop()
    if any(line == b"" for line in physical_lines):
        errors.append(f"{path.name}: contém linha vazia inválida")
    for line_number, line in enumerate(physical_lines, start=1):
        if len(line) > 75:
            errors.append(f"{path.name}:{line_number}: linha ICS excede 75 octetos")

    try:
        calendar = Calendar.from_ical(data)
    except Exception as exc:  # icalendar raises multiple parse exception classes.
        errors.append(f"{path.name}: icalendar não conseguiu analisar: {exc}")
        return errors
    if calendar.name != "VCALENDAR":
        errors.append(f"{path.name}: componente raiz não é VCALENDAR")
        return errors
    if str(calendar.get("VERSION", "")) != "2.0":
        errors.append(f"{path.name}: VERSION deve ser 2.0")

    seen_uids: set[str] = set()
    for index, event in enumerate(calendar.walk("VEVENT"), start=1):
        uid = str(event.get("UID", "")).strip()
        if not uid:
            errors.append(f"{path.name}: VEVENT {index} sem UID")
        elif uid in seen_uids:
            errors.append(f"{path.name}: UID duplicado: {uid}")
        seen_uids.add(uid)
        if event.get("DTSTART") is None:
            errors.append(f"{path.name}: VEVENT {index} sem DTSTART")
            continue
        if event.get("DTEND") is None:
            dtstart = event.decoded("DTSTART")
            if not (isinstance(dtstart, date) and not isinstance(dtstart, datetime)):
                errors.append(f"{path.name}: VEVENT {index} sem DTEND")
    return errors


def validate_directory(docs_dir: Path = DOCS_DIR) -> list[str]:
    files = sorted(docs_dir.glob("*.ics"))
    if not files:
        return [f"nenhum arquivo ICS encontrado em {docs_dir}"]
    errors: list[str] = []
    for path in files:
        errors.extend(validate_file(path))
    return errors


def main() -> int:
    errors = validate_directory()
    if errors:
        for error in errors:
            print(f"ERRO: {error}")
        return 1
    files = sorted(DOCS_DIR.glob("*.ics"))
    print(f"Validação ICS concluída: {len(files)} arquivo(s) válido(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
