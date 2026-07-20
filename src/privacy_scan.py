"""Fail closed when public artifacts contain private calendar data or credentials."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .config import DATA_DIR, DOCS_DIR, PROJECT_ROOT

EMAIL = re.compile(r"(?<![a-z0-9])([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})(?![a-z0-9])", re.I)
PRIVATE_URL = re.compile(r"https?://(?:calendar\.google\.com|meet\.google\.com|(?:www\.)?zoom\.us)\S*", re.I)
SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._-]{20,}|(?:access|refresh|sync|export)[_-]?token\s*[:=]\s*['\"]?[a-z0-9_-]{24,})"
)
RAW_GOOGLE_EVENT = re.compile(r"\b[a-z0-9]{16,}@google\.com\b", re.I)


def scan_text(text: str, label: str = "conteúdo") -> list[str]:
    issues: list[str] = []
    sanitized = text.replace("@sports-calendar-hub", "")
    emails = sorted({match.group(1) for match in EMAIL.finditer(sanitized)})
    if emails:
        issues.append(f"{label}: e-mail encontrado")
    if PRIVATE_URL.search(text):
        issues.append(f"{label}: link privado de calendário/conferência encontrado")
    if SECRET_VALUE.search(text):
        issues.append(f"{label}: provável credencial encontrada")
    if RAW_GOOGLE_EVENT.search(text):
        issues.append(f"{label}: ID bruto do Google Calendar encontrado")
    return issues


def scan_payload(payload: Any, label: str = "payload") -> list[str]:
    return scan_text(json.dumps(payload, ensure_ascii=False), label)


def default_public_files() -> Iterable[Path]:
    yield DATA_DIR / "events.json"
    if DOCS_DIR.exists():
        yield from DOCS_DIR.glob("*")
    reports = PROJECT_ROOT / "reports"
    if reports.exists():
        yield from reports.glob("*.json")
        yield from reports.glob("*.md")


def scan_files(paths: Iterable[Path]) -> list[str]:
    issues: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        issues.extend(scan_text(text, str(path.relative_to(PROJECT_ROOT))))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    issues = scan_files(args.paths or list(default_public_files()))
    print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
