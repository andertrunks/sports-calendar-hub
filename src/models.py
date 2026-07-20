"""Typed event model and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.parser import isoparse

from .config import ALLOWED_STATUSES, COLOR_GROUPS, DEFAULT_TIMEZONE


def _aware_datetime(value: Any, timezone_name: str, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = isoparse(value.strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} inválido: {value!r}") from exc
    else:
        raise ValueError(f"{field_name} é obrigatório")

    zone = ZoneInfo(timezone_name)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed


@dataclass(slots=True)
class SportsEvent:
    source_id: str = ""
    source_name: str = ""
    external_id: str = ""
    title: str = ""
    sport: str = ""
    category: str = ""
    competition: str = ""
    phase: str = ""
    participant_1: str = ""
    participant_2: str = ""
    start: datetime | None = None
    end: datetime | None = None
    timezone: str = DEFAULT_TIMEZONE
    all_day: bool = False
    location: str = ""
    city: str = ""
    country: str = ""
    broadcaster_br: str = ""
    status: str = "CONFIRMED"
    source_url: str = ""
    color_group: str = "outros-esportes"
    priority: int = 0
    last_verified: datetime | None = None
    sequence: int = 0

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("title não pode ser vazio")

        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"fuso inválido: {self.timezone}") from exc

        if self.start is None:
            raise ValueError("start é obrigatório")
        if self.start.tzinfo is None:
            self.start = self.start.replace(tzinfo=zone)
        if self.end is not None and self.end.tzinfo is None:
            self.end = self.end.replace(tzinfo=zone)

        if not self.all_day:
            if self.end is None:
                raise ValueError("end é obrigatório para evento com horário")
            if self.end <= self.start:
                raise ValueError("end deve ser posterior a start")

        self.status = self.status.upper()
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"status inválido: {self.status}")
        if self.color_group not in COLOR_GROUPS:
            raise ValueError(f"color_group inválido: {self.color_group}")
        if self.sequence < 0:
            raise ValueError("sequence não pode ser negativo")
        if self.last_verified is None:
            self.last_verified = self.start.astimezone(UTC)
        elif self.last_verified.tzinfo is None:
            self.last_verified = self.last_verified.replace(tzinfo=zone)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SportsEvent":
        timezone_name = str(data.get("timezone") or DEFAULT_TIMEZONE)
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"fuso inválido: {timezone_name}") from exc

        start = _aware_datetime(data.get("start"), timezone_name, "start")
        raw_end = data.get("end")
        end = _aware_datetime(raw_end, timezone_name, "end") if raw_end else None
        raw_verified = data.get("last_verified")
        last_verified = (
            _aware_datetime(raw_verified, timezone_name, "last_verified")
            if raw_verified
            else start.astimezone(UTC)
        )
        return cls(
            source_id=str(data.get("source_id") or ""),
            source_name=str(data.get("source_name") or ""),
            external_id=str(data.get("external_id") or ""),
            title=str(data.get("title") or ""),
            sport=str(data.get("sport") or ""),
            category=str(data.get("category") or ""),
            competition=str(data.get("competition") or ""),
            phase=str(data.get("phase") or ""),
            participant_1=str(data.get("participant_1") or ""),
            participant_2=str(data.get("participant_2") or ""),
            start=start,
            end=end,
            timezone=timezone_name,
            all_day=bool(data.get("all_day", False)),
            location=str(data.get("location") or ""),
            city=str(data.get("city") or ""),
            country=str(data.get("country") or ""),
            broadcaster_br=str(data.get("broadcaster_br") or ""),
            status=str(data.get("status") or "CONFIRMED"),
            source_url=str(data.get("source_url") or ""),
            color_group=str(data.get("color_group") or "outros-esportes"),
            priority=int(data.get("priority", 0)),
            last_verified=last_verified,
            sequence=int(data.get("sequence", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("start", "end", "last_verified"):
            value = result[key]
            result[key] = value.isoformat() if value is not None else None
        return result
