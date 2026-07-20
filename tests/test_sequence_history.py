from __future__ import annotations

from dataclasses import replace

from src.calendar_payload import preserve_uid_and_sequence
from src.normalize import permanent_uid
from tests import make_event


def test_horario_alterado_preserva_uid_e_incrementa_sequence() -> None:
    old = make_event(external_id="hash", sequence=4)
    new = replace(old, start=old.start.replace(hour=22), end=old.end.replace(hour=23), uid="")
    [result], counts = preserve_uid_and_sequence([new], [old])
    assert permanent_uid(result) == permanent_uid(old)
    assert result.sequence == 5
    assert counts["updated"] == 1


def test_last_verified_isolado_nao_incrementa_sequence() -> None:
    old = make_event(external_id="hash", sequence=4)
    new = replace(old, last_verified=old.last_verified.replace(hour=11))
    [result], counts = preserve_uid_and_sequence([new], [old])
    assert result.sequence == 4
    assert counts["unchanged"] == 1


def test_cancelamento_incrementa_sequence() -> None:
    old = make_event(external_id="hash", sequence=2)
    new = replace(old, status="CANCELLED")
    [result], _ = preserve_uid_and_sequence([new], [old])
    assert result.sequence == 3


def test_execucao_repetida_e_idempotente() -> None:
    event = make_event(external_id="hash", sequence=0)
    [first], _ = preserve_uid_and_sequence([event], [])
    [second], counts = preserve_uid_and_sequence([first], [first])
    assert second.sequence == first.sequence
    assert counts["unchanged"] == 1
