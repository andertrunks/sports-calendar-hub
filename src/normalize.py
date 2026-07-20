"""Normalization, grouping and permanent UID helpers."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import replace

from .config import UID_DOMAIN
from .models import SportsEvent
from .scope_rules import determine_color_group, normalize_team_name

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
    return normalize_team_name(value)


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


def assign_color_group(event: SportsEvent) -> str:
    return determine_color_group(event)


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
