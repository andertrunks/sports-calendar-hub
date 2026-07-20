from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.calendar_push import validate_gateway_response

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_resposta_dry_run_valida() -> None:
    response = _fixture("calendar_dry_run_response.json")
    plan = validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=True, event_count=2)
    assert plan["create"] == 1


def test_resposta_apply_valida() -> None:
    response = _fixture("calendar_apply_response.json")
    validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=False, event_count=2)


def test_resposta_com_hash_adulterado_falha() -> None:
    response = _fixture("calendar_dry_run_response.json")
    with pytest.raises(ValueError, match="source_hash"):
        validate_gateway_response(response, source_hash="outro", dry_run=True, event_count=2)


def test_erro_do_gateway_inclui_detalhe_sanitizado() -> None:
    response = {"ok": False, "error": "apply_failed", "detail": "invalid_sequence"}
    with pytest.raises(ValueError, match="invalid_sequence"):
        validate_gateway_response(response, source_hash="hash", dry_run=False, event_count=1)


def test_exclusao_em_massa_falha() -> None:
    response = _fixture("calendar_dry_run_response.json")
    response["plan"]["delete"] = 3
    with pytest.raises(ValueError, match="25%"):
        validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=True, event_count=10)


def test_exclusao_no_calendario_principal_falha() -> None:
    response = _fixture("calendar_dry_run_response.json")
    response["plan"]["primary_delete"] = 1
    with pytest.raises(ValueError, match="principal"):
        validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=True, event_count=2)


def test_duplicata_esportiva_nao_resolvida_falha() -> None:
    response = _fixture("calendar_dry_run_response.json")
    response["plan"]["duplicate_reviews"] = 1
    with pytest.raises(ValueError, match="duplicidade"):
        validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=True, event_count=2)


def test_duplicatas_confirmadas_nao_contam_como_exclusao_de_escopo() -> None:
    response = _fixture("calendar_dry_run_response.json")
    response["plan"].update({
        "delete": 30,
        "duplicate_delete": 30,
        "scope_delete": 0,
        "existing_future": 100,
        "duplicate_reviews": 0,
    })
    validate_gateway_response(response, source_hash="fixture-source-hash", dry_run=True, event_count=2)
