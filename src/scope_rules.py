"""Machine-readable project scope and deterministic classification rules."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .models import SportsEvent

_HTML_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    cleaned = html.unescape(_HTML_TAG.sub(" ", value or "")).casefold()
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACE.sub(" ", re.sub(r"[^a-z0-9]+", " ", without_accents)).strip()


@lru_cache(maxsize=4)
def _load_scope_rules_cached(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "updated_at",
        "timezone",
        "horizon_months",
        "groups",
        "group_priority",
        "teams",
        "team_aliases",
        "allowed_team_categories",
        "excluded_team_categories",
        "competitions",
        "competition_aliases",
        "competition_phase_filters",
        "sport_rules",
        "tennis_rules",
        "motorsport_rules",
        "brazilian_national_teams",
        "deduplication_rules",
        "transmission_rules",
        "title_patterns",
        "prohibited_data_fields",
    }
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"scope_rules.json sem campos obrigatórios: {sorted(missing)}")

    team_aliases = {_normalize(alias): canonical for alias, canonical in payload["team_aliases"].items()}
    for canonical, definition in payload["teams"].items():
        team_aliases.setdefault(_normalize(canonical), canonical)
        team_aliases.setdefault(_normalize(definition["display_name"]), canonical)

    competition_aliases = {
        _normalize(alias): canonical for alias, canonical in payload["competition_aliases"].items()
    }
    for canonical, definition in payload["competitions"].items():
        competition_aliases.setdefault(_normalize(canonical), canonical)
        competition_aliases.setdefault(_normalize(definition["display_name"]), canonical)

    payload["_team_alias_lookup"] = team_aliases
    payload["_competition_alias_lookup"] = competition_aliases
    return payload


def load_scope_rules(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the canonical project scope."""

    resolved = (path or DATA_DIR / "scope_rules.json").resolve()
    return _load_scope_rules_cached(str(resolved))


def identify_team(value: str, rules: dict[str, Any] | None = None) -> str | None:
    rules = rules or load_scope_rules()
    normalized = _normalize(value)
    if not normalized:
        return None
    direct = rules["_team_alias_lookup"].get(normalized)
    if direct:
        return direct
    if normalized.startswith("sao paulo "):
        return "sao-paulo"
    if normalized.startswith("selecao brasileira ") or normalized.startswith("brasil "):
        return "brasil"
    return None


def normalize_team_name(value: str, rules: dict[str, Any] | None = None) -> str:
    """Return a stable canonical team identifier when the alias is known."""

    return identify_team(value, rules) or _normalize(value)


def identify_competition(value: str, rules: dict[str, Any] | None = None) -> str | None:
    rules = rules or load_scope_rules()
    normalized = _normalize(value)
    if not normalized:
        return None
    direct = rules["_competition_alias_lookup"].get(normalized)
    if direct:
        return direct
    for alias, canonical in sorted(
        rules["_competition_alias_lookup"].items(), key=lambda item: len(item[0]), reverse=True
    ):
        if len(alias) >= 8 and alias in normalized:
            return canonical
    if normalized == "cspj":
        return "copinha"
    return None


def identify_age_category(value: str) -> str:
    normalized = _normalize(value)
    gender = "female" if "feminin" in normalized else "male" if "masculin" in normalized else "unknown"
    age_match = re.search(r"(?:sub|u)\s*(\d{2})", normalized)
    if age_match:
        return f"{gender}-u{age_match.group(1)}"
    if gender == "female" and "base" in normalized:
        return "female-youth"
    if gender == "male" and "base" in normalized:
        return "male-youth"
    if gender in {"female", "male"}:
        return f"{gender}-professional"
    return "unknown"


def _team_ids(event: SportsEvent, rules: dict[str, Any]) -> set[str]:
    return {
        team
        for team in (
            identify_team(event.participant_1, rules),
            identify_team(event.participant_2, rules),
        )
        if team
    }


def _team_groups(event: SportsEvent, rules: dict[str, Any]) -> set[str]:
    return {rules["teams"][team]["group"] for team in _team_ids(event, rules) if team in rules["teams"]}


def is_excluded_sao_paulo_female_youth(
    event: SportsEvent, rules: dict[str, Any] | None = None
) -> bool:
    rules = rules or load_scope_rules()
    if "sao-paulo" not in _team_ids(event, rules):
        return False
    category = identify_age_category(event.category)
    excluded = set(rules["excluded_team_categories"]["sao-paulo"])
    normalized_category = _normalize(event.category)
    return category in excluded or (
        "feminin" in normalized_category
        and ("base" in normalized_category or re.search(r"(?:sub|u)\s*\d{2}", normalized_category))
    )


def _phase_allowed(phase: str, allowed: list[str]) -> bool:
    normalized_phase = _normalize(phase)
    return any(_normalize(item) in normalized_phase for item in allowed)


def is_copinha_event_allowed(event: SportsEvent, rules: dict[str, Any] | None = None) -> bool:
    rules = rules or load_scope_rules()
    if identify_competition(event.competition, rules) != "copinha":
        return True
    allowed = rules["competition_phase_filters"]["copinha"]
    if _phase_allowed(event.phase, allowed):
        return True
    return "sao-paulo" in _team_ids(event, rules) and identify_age_category(event.category) in {
        "male-u20",
        "male-u17",
    }


def _is_motorsport_in_scope(event: SportsEvent, rules: dict[str, Any]) -> bool:
    text = _normalize(" ".join((event.sport, event.category, event.competition, event.phase, event.title)))
    motor = rules["motorsport_rules"]
    known_competition = any(_normalize(name) in text for name in motor["competitions"])
    allowed_session = any(_normalize(name) in text for name in motor["allowed_sessions"])
    excluded_session = any(_normalize(name) in text for name in motor["excluded_sessions"])
    return known_competition and allowed_session and not excluded_session


def _is_tennis_in_scope(event: SportsEvent, rules: dict[str, Any]) -> bool:
    text = _normalize(" ".join((event.category, event.competition, event.phase, event.title)))
    tennis = rules["tennis_rules"]
    if tennis["singles_only"] and any(word in text for word in ("dupla", "doubles", "mixed doubles")):
        return False
    if tennis["require_opponent_date_time"] and (
        not event.participant_1 or not event.participant_2 or event.all_day
    ):
        return False
    priority_players = {_normalize(name) for name in tennis["priority_players"]}
    participants = {_normalize(event.participant_1), _normalize(event.participant_2)}
    if priority_players & participants:
        return True
    for competition, allowed_phases in tennis["phase_filters"].items():
        if _normalize(competition) in text:
            return _phase_allowed(event.phase, allowed_phases)
    grand_slams = ("australian open", "roland garros", "wimbledon", "us open")
    if any(name in text for name in grand_slams):
        return _phase_allowed(event.phase, tennis["phase_filters"]["Grand Slam"])
    return False


def is_event_in_scope(event: SportsEvent, rules: dict[str, Any] | None = None) -> bool:
    """Apply exclusions first, then the complete master-scope inclusion rules."""

    rules = rules or load_scope_rules()
    if is_excluded_sao_paulo_female_youth(event, rules):
        return False

    sport = _normalize(event.sport)
    category = identify_age_category(event.category)
    competition = identify_competition(event.competition, rules)
    team_ids = _team_ids(event, rules)
    team_groups = _team_groups(event, rules)

    if competition == "copinha":
        return is_copinha_event_allowed(event, rules)

    if "sao-paulo" in team_ids:
        return category in set(rules["allowed_team_categories"]["sao-paulo"])
    if "brasil" in team_ids:
        return True
    if "clubes-regionais" in team_groups:
        return category in set(rules["allowed_team_categories"]["clubes-regionais"])
    if "red-bull" in team_groups:
        return category in set(rules["allowed_team_categories"]["red-bull"])

    if any(term in sport for term in ("automobilismo", "motorsport")):
        return _is_motorsport_in_scope(event, rules)
    if "tenis" in sport or "tennis" in sport:
        return _is_tennis_in_scope(event, rules)

    if "futebol" in sport or "football" in sport:
        if "brasileirao" in team_groups or "premier-league" in team_groups:
            return category == "male-professional"
        if competition in {"mundial-clubes", "intercontinental", "copa-do-mundo"}:
            return True
        if competition in rules["competition_phase_filters"]:
            return _phase_allowed(event.phase, rules["competition_phase_filters"][competition])
        competition_text = _normalize(event.competition)
        national_terms = (
            "eurocopa",
            "copa america",
            "copa africana",
            "copa da asia",
            "copa ouro",
            "liga das nacoes",
            "eliminatorias",
        )
        if any(term in competition_text for term in national_terms):
            return True

    if competition in {"olimpiadas", "pan-americanos"}:
        text = _normalize(" ".join((event.title, event.phase, event.participant_1, event.participant_2)))
        return "brasil" in text or any(term in text for term in ("medalha", "final"))

    combined = _normalize(" ".join((event.sport, event.competition, event.phase, event.title)))
    if "nfl" in combined:
        return "new york giants" in combined or any(
            term in combined for term in ("wild card", "divisional", "final da", "super bowl")
        )
    if competition in {"world-series", "nba-finals", "mls-cup"}:
        return True
    if "brasil" in _normalize(" ".join((event.participant_1, event.participant_2))):
        return True
    return False


def determine_color_group(event: SportsEvent, rules: dict[str, Any] | None = None) -> str:
    """Choose exactly one feed using the public group-priority contract."""

    rules = rules or load_scope_rules()
    team_ids = _team_ids(event, rules)
    team_groups = _team_groups(event, rules)
    competition = identify_competition(event.competition, rules)
    sport = _normalize(event.sport)

    if "sao-paulo" in team_ids:
        return "sao-paulo"
    if "brasil" in team_ids:
        return "selecao-brasileira"
    if "clubes-regionais" in team_groups:
        return "clubes-regionais"
    if "red-bull" in team_groups:
        return "red-bull"
    if competition == "copinha":
        return "outros-esportes"
    if "premier-league" in team_groups or competition == "premier-league":
        return "premier-league"
    if competition in {
        "libertadores",
        "sul-americana",
        "champions-league",
        "europa-league",
        "conference-league",
        "mundial-clubes",
        "intercontinental",
    }:
        return "continentais"
    if any(term in sport for term in ("automobilismo", "motorsport")):
        return "automobilismo"
    if "brasileirao" in team_groups or competition == "brasileirao-serie-a":
        return "brasileirao"
    if competition in {"olimpiadas", "pan-americanos"}:
        return "olimpiadas-pan"
    if competition == "copa-do-mundo":
        return "copas-do-mundo"
    return "outros-esportes"


def determine_priority(event: SportsEvent, rules: dict[str, Any] | None = None) -> int:
    rules = rules or load_scope_rules()
    group = determine_color_group(event, rules)
    index = rules["group_priority"].index(group)
    return (len(rules["group_priority"]) - index) * 100

