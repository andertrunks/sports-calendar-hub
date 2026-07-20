"""Normalization, grouping and permanent UID helpers."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import replace

from .config import UID_DOMAIN
from .models import SportsEvent

_HTML_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_MATCHUP_SEPARATOR = re.compile(r"\s+(?:x|vs\.?|versus|×)\s+", re.IGNORECASE)


def remove_html(value: str) -> str:
    return html.unescape(_HTML_TAG.sub(" ", value or ""))


def collapse_spaces(value: str) -> str:
    return _SPACE.sub(" ", value or "").strip()


def clean_display_text(value: str) -> str:
    return collapse_spaces(remove_html(value))


def normalize_for_comparison(value: str) -> str:
    cleaned = clean_display_text(value).casefold()
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    without_punctuation = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return collapse_spaces(without_punctuation)


def normalize_participant(value: str) -> str:
    normalized = normalize_for_comparison(value)
    aliases = {
        "sao paulo fc": "sao paulo",
        "sao paulo futebol clube": "sao paulo",
        "red bull bragantino sp": "red bull bragantino",
        "selecao do brasil": "brasil",
        "selecao brasileira": "brasil",
    }
    return aliases.get(normalized, normalized)


def split_matchup(value: str) -> tuple[str, str] | None:
    parts = _MATCHUP_SEPARATOR.split(clean_display_text(value), maxsplit=1)
    if len(parts) != 2 or not all(parts):
        return None
    return parts[0], parts[1]


def canonical_participants(event: SportsEvent) -> tuple[str, ...]:
    participants = [
        normalize_participant(event.participant_1),
        normalize_participant(event.participant_2),
    ]
    return tuple(sorted(participant for participant in participants if participant))


def canonical_event_key(event: SportsEvent) -> str:
    fields = (
        normalize_for_comparison(event.sport),
        normalize_for_comparison(event.category),
        normalize_for_comparison(event.competition),
        normalize_for_comparison(event.phase),
        *canonical_participants(event),
    )
    return "|".join(fields)


def permanent_uid(event: SportsEvent) -> str:
    source = normalize_for_comparison(event.source_id or event.source_name) or "unknown-source"
    external = normalize_for_comparison(event.external_id)
    if external:
        identity = f"external|{source}|{external}"
    else:
        identity = "|".join(
            (
                "canonical",
                source,
                normalize_for_comparison(event.sport),
                normalize_for_comparison(event.competition),
                normalize_for_comparison(event.category),
                *canonical_participants(event),
                normalize_for_comparison(event.phase),
            )
        )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"{digest}@{UID_DOMAIN}"


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def assign_color_group(event: SportsEvent) -> str:
    participants = " | ".join(canonical_participants(event))
    competition = normalize_for_comparison(event.competition)
    sport = normalize_for_comparison(event.sport)
    category = normalize_for_comparison(event.category)

    # This order is the public priority contract. The first match wins.
    if re.search(r"(^|\| )sao paulo($| \|)", participants):
        return "sao-paulo"
    if any(participant in {"brasil", "brasil feminino", "brasil sub 20", "brasil sub 23"}
           for participant in canonical_participants(event)):
        return "selecao-brasileira"
    if _contains_any(participants, ("ferroviaria", "corinthians", "palmeiras", "santos")):
        return "clubes-regionais"
    if _contains_any(participants, ("red bull", "rb leipzig", "rb salzburg")):
        return "red-bull"
    if "premier league" in competition:
        return "premier-league"
    if _contains_any(
        competition,
        (
            "libertadores",
            "sul americana",
            "champions league",
            "europa league",
            "conference league",
            "recopa sul americana",
        ),
    ):
        return "continentais"
    if _contains_any(sport + " " + category + " " + competition, ("automobilismo", "formula 1", "formula 2", "formula 3", "formula 4", "f4")):
        return "automobilismo"
    if _contains_any(competition, ("brasileirao", "campeonato brasileiro", "serie a brasileira")):
        return "brasileirao"
    if _contains_any(competition, ("olimpiada", "olimpico", "jogos pan americanos", "pan americano")):
        return "olimpiadas-pan"
    if _contains_any(competition, ("copa do mundo", "world cup")):
        return "copas-do-mundo"
    return "outros-esportes"


def normalize_event(event: SportsEvent) -> SportsEvent:
    text_fields = {
        field: clean_display_text(getattr(event, field))
        for field in (
            "source_id",
            "source_name",
            "external_id",
            "title",
            "sport",
            "category",
            "competition",
            "phase",
            "participant_1",
            "participant_2",
            "location",
            "city",
            "country",
            "broadcaster_br",
            "source_url",
        )
    }
    normalized = replace(event, **text_fields)
    return replace(normalized, color_group=assign_color_group(normalized))
