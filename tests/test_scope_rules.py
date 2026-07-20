from __future__ import annotations

from src.scope_rules import (
    determine_color_group,
    identify_team,
    is_copinha_event_allowed,
    is_event_in_scope,
    is_excluded_sao_paulo_female_youth,
    load_scope_rules,
)
from tests import make_event


def _football(**overrides):
    defaults = {
        "category": "Masculino profissional",
        "competition": "Copa do Brasil 2026",
        "phase": "Quartas de final",
        "participant_1": "Equipe A",
        "participant_2": "Equipe B",
    }
    defaults.update(overrides)
    return make_event(**defaults)


def test_botafogo_sp_pertence_a_clubes_regionais() -> None:
    event = _football(participant_1="Botafogo-SP", participant_2="Palmeiras")
    assert is_event_in_scope(event)
    assert determine_color_group(event) == "clubes-regionais"


def test_botafogo_ribeirao_e_alias_de_botafogo_sp() -> None:
    assert identify_team("Botafogo de Ribeirão Preto") == "botafogo-sp"


def test_botafogo_sp_nao_e_confundido_com_botafogo_rj() -> None:
    assert identify_team("Botafogo-SP") == "botafogo-sp"
    assert identify_team("Botafogo de Futebol e Regatas") == "botafogo-rj"
    assert identify_team("Botafogo") == "botafogo-rj"


def test_comercial_sp_pertence_a_clubes_regionais() -> None:
    event = _football(participant_1="Comercial-SP", participant_2="Equipe B")
    assert is_event_in_scope(event)
    assert determine_color_group(event) == "clubes-regionais"


def test_comercial_ribeirao_e_alias_de_comercial_sp() -> None:
    assert identify_team("Comercial de Ribeirão Preto") == "comercial-sp"


def test_sao_paulo_feminino_profissional_permanece_no_escopo() -> None:
    event = _football(category="Feminino profissional", participant_1="São Paulo")
    assert is_event_in_scope(event)
    assert not is_excluded_sao_paulo_female_youth(event)


def test_sao_paulo_feminino_sub20_e_excluido() -> None:
    event = _football(category="Feminino sub-20", participant_1="São Paulo")
    assert is_excluded_sao_paulo_female_youth(event)
    assert not is_event_in_scope(event)


def test_sao_paulo_feminino_sub17_e_excluido() -> None:
    event = _football(category="Feminino sub-17", participant_1="São Paulo")
    assert is_excluded_sao_paulo_female_youth(event)
    assert not is_event_in_scope(event)


def test_outra_equipe_feminina_de_base_do_sao_paulo_e_excluida() -> None:
    event = _football(category="Feminino de base", participant_1="São Paulo feminino")
    assert is_excluded_sao_paulo_female_youth(event)
    assert not is_event_in_scope(event)


def test_sao_paulo_masculino_sub20_permanece_no_escopo() -> None:
    assert is_event_in_scope(_football(category="Masculino sub-20", participant_1="São Paulo"))


def test_sao_paulo_masculino_sub17_permanece_no_escopo() -> None:
    assert is_event_in_scope(_football(category="Masculino sub-17", participant_1="São Paulo"))


def test_copinha_nas_oitavas_e_incluida() -> None:
    event = _football(competition="Copinha", phase="Oitavas de final", category="Masculino sub-20")
    assert is_copinha_event_allowed(event)
    assert is_event_in_scope(event)


def test_copinha_nas_quartas_e_incluida() -> None:
    event = _football(competition="Copa São Paulo", phase="Quartas de final", category="Masculino sub-20")
    assert is_copinha_event_allowed(event)


def test_copinha_na_semifinal_e_incluida() -> None:
    event = _football(competition="Copa SP de Futebol Júnior", phase="Semifinal", category="Masculino sub-20")
    assert is_copinha_event_allowed(event)


def test_copinha_na_final_e_incluida() -> None:
    event = _football(competition="Copa São Paulo de Juniores", phase="Final", category="Masculino sub-20")
    assert is_copinha_event_allowed(event)


def test_copinha_na_fase_de_grupos_e_excluida_pela_regra_geral() -> None:
    event = _football(competition="Copinha", phase="Fase de grupos", category="Masculino sub-20")
    assert not is_copinha_event_allowed(event)
    assert not is_event_in_scope(event)


def test_sao_paulo_em_fase_anterior_da_copinha_permanece() -> None:
    event = _football(
        competition="Copinha",
        phase="Segunda fase",
        category="Masculino sub-20",
        participant_1="São Paulo",
    )
    assert is_copinha_event_allowed(event)
    assert is_event_in_scope(event)
    assert determine_color_group(event) == "sao-paulo"


def test_palmeiras_santos_oitavas_copinha_vai_para_outros_esportes() -> None:
    event = _football(
        competition="Copinha",
        phase="Oitavas de final",
        category="Masculino sub-20",
        participant_1="Palmeiras",
        participant_2="Santos",
    )
    assert is_event_in_scope(event)
    assert determine_color_group(event) == "outros-esportes"


def test_sao_paulo_palmeiras_copinha_vai_para_sao_paulo() -> None:
    event = _football(
        competition="Copinha",
        phase="Oitavas de final",
        category="Masculino sub-20",
        participant_1="São Paulo",
        participant_2="Palmeiras",
    )
    assert determine_color_group(event) == "sao-paulo"


def test_botafogo_sp_palmeiras_vai_para_clubes_regionais() -> None:
    event = _football(participant_1="Botafogo-SP", participant_2="Palmeiras")
    assert determine_color_group(event) == "clubes-regionais"


def test_comercial_sp_sao_paulo_vai_para_sao_paulo() -> None:
    event = _football(participant_1="Comercial-SP", participant_2="São Paulo")
    assert determine_color_group(event) == "sao-paulo"


def test_scope_json_contem_contrato_minimo() -> None:
    rules = load_scope_rules()
    assert rules["timezone"] == "America/Sao_Paulo"
    assert rules["group_priority"][0] == "sao-paulo"
    assert "prohibited_data_fields" in rules

