"""End-to-end Sheet export, ICS generation and Google Calendar UPSERT pipeline."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from .calendar_payload import build_sync_payload
from .calendar_push import post_json, validate_gateway_response
from .config import DATA_DIR, DOCS_DIR, PROJECT_ROOT
from .ics_generator import generate_calendars, generate_index
from .importers.apps_script_json import import_export, validate_export
from .main import load_events
from .privacy_scan import scan_files, scan_payload
from .sync_report import build_report, write_report
from .validate_ics import validate_directory


def download_export(url: str, token: str, timeout: int = 120) -> dict:
    separator = "&" if "?" in url else "?"
    target = f"{url}{separator}{urlencode({'action': 'export', 'token': token})}"
    with urlopen(target, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    validate_export(payload)
    return payload


def run(*, gateway_url: str, export_token: str, sync_token: str) -> dict:
    export = download_export(gateway_url, export_token)
    events, import_summary = import_export(export, DATA_DIR / "events.json")
    counts, _ = generate_calendars(events, DOCS_DIR)
    generated_at = max(event.last_verified for event in events)
    generate_index(counts, generated_at, DOCS_DIR)
    validation_errors = validate_directory(DOCS_DIR)
    if validation_errors:
        raise ValueError(f"ICS inválido: {validation_errors}")
    privacy_issues = scan_files([DATA_DIR / "events.json", *DOCS_DIR.glob("*")])
    if privacy_issues:
        raise ValueError(f"falha de privacidade: {privacy_issues}")

    dry_payload = build_sync_payload(events, dry_run=True)
    payload_issues = scan_payload(dry_payload, "calendar dry-run payload")
    if payload_issues:
        raise ValueError(f"payload inseguro: {payload_issues}")
    dry_response = post_json(gateway_url, dry_payload, sync_token)
    validate_gateway_response(
        dry_response,
        source_hash=dry_payload["source_hash"],
        dry_run=True,
        event_count=len(events),
    )

    apply_payload = build_sync_payload(events, dry_run=False)
    apply_response = post_json(gateway_url, apply_payload, sync_token)
    validate_gateway_response(
        apply_response,
        source_hash=apply_payload["source_hash"],
        dry_run=False,
        event_count=len(events),
    )
    report = build_report(events, import_summary, dry_response, apply_response)
    write_report(PROJECT_ROOT / "reports" / "sync-latest.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-url", default=os.environ.get("SPORTS_GATEWAY_URL"))
    args = parser.parse_args()
    export_token = os.environ.get("SPORTS_EXPORT_TOKEN")
    sync_token = os.environ.get("SPORTS_SYNC_TOKEN")
    if not args.gateway_url or not export_token or not sync_token:
        raise SystemExit("SPORTS_GATEWAY_URL, SPORTS_EXPORT_TOKEN e SPORTS_SYNC_TOKEN são obrigatórios")
    report = run(gateway_url=args.gateway_url, export_token=export_token, sync_token=sync_token)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
