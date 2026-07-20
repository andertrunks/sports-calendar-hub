"""HTTPS client and response gates for the Apps Script calendar gateway."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from .calendar_payload import SCHEMA_VERSION

MAX_DELETE_RATIO = 0.25


def post_json(
    url: str,
    payload: dict[str, Any],
    token: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: int = 120,
) -> dict[str, Any]:
    body = dict(payload)
    body["token"] = token
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with opener(request, timeout=timeout) as response:
        raw = response.read()
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("resposta do gateway não é objeto JSON")
    return result


def validate_gateway_response(
    response: dict[str, Any], *, source_hash: str, dry_run: bool, event_count: int
) -> dict[str, Any]:
    if response.get("ok") is not True:
        raise ValueError(f"gateway recusou a sincronização: {response.get('error', 'erro desconhecido')}")
    if response.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("gateway respondeu com schema incompatível")
    if response.get("source_hash") != source_hash:
        raise ValueError("gateway respondeu com source_hash diferente")
    if bool(response.get("dry_run")) is not dry_run:
        raise ValueError("gateway respondeu com modo dry_run diferente")
    if response.get("calendar") != "Eventos esportivos":
        raise ValueError("gateway não confirmou o calendário Eventos esportivos")
    blockers = response.get("blockers") or []
    if blockers:
        raise ValueError(f"gateway informou bloqueios críticos: {blockers}")
    plan = response.get("plan") or {}
    deletes = int(plan.get("delete", 0) or 0)
    scope_deletes = int(plan.get("scope_delete", deletes) or 0)
    deletion_base = int(plan.get("existing_future", event_count) or event_count)
    if deletion_base and scope_deletes / deletion_base > MAX_DELETE_RATIO:
        raise ValueError("dry-run planejou exclusão superior a 25%")
    if int(plan.get("duplicate_reviews", 0) or 0):
        raise ValueError("dry-run deixou duplicidade esportiva sem resolução")
    if int(plan.get("primary_delete", 0) or 0):
        raise ValueError("dry-run planejou exclusão automática no calendário principal")
    if int(plan.get("missing_uid", 0) or 0):
        raise ValueError("dry-run encontrou evento sem UID")
    if int(plan.get("privacy_violations", 0) or 0):
        raise ValueError("dry-run encontrou participantes, conferência ou conteúdo privado")
    return plan
