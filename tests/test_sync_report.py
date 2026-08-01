from __future__ import annotations

from src.sync_report import build_report
from tests import make_event


def test_report_ignora_ids_de_execucao_volateis() -> None:
    events = [make_event()]
    import_summary = {
        "source_hash": "hash-estavel",
        "source_rows": 1,
        "in_scope": 1,
        "unique_events": 1,
        "deduplicated": 0,
        "changes": {"created": 0, "updated": 0, "unchanged": 1},
    }
    first_dry = {"execution_id": "dry-1", "plan": {"unchanged": 1}}
    first_apply = {
        "execution_id": "apply-1",
        "plan": {"unchanged": 1},
        "result": {"unchanged": 1},
    }
    second_dry = {"execution_id": "dry-2", "plan": {"unchanged": 1}}
    second_apply = {
        "execution_id": "apply-2",
        "plan": {"unchanged": 1},
        "result": {"unchanged": 1},
    }

    first = build_report(events, import_summary, first_dry, first_apply)
    second = build_report(events, import_summary, second_dry, second_apply)

    assert first == second
    assert "execution_id" not in first["dry_run"]
    assert "execution_id" not in first["apply"]
