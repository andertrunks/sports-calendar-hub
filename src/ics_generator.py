"""Generate deterministic iCalendar feeds and the public index page."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from .config import DEFAULT_TIMEZONE, FEED_METADATA, PRODID
from .models import SportsEvent
from .normalize import permanent_uid


def _write_bytes_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def _description(event: SportsEvent) -> str:
    lines = [
        "DADOS DE DEMONSTRAÇÃO — NÃO É CALENDÁRIO OFICIAL",
        f"📺 Transmissão no Brasil: {event.broadcaster_br or 'ainda não confirmada'}",
    ]
    if event.competition:
        lines.append(f"🏆 Competição: {event.competition}")
    if event.phase:
        lines.append(f"📍 Fase/Rodada: {event.phase}")
    if event.location:
        lines.append(f"🏟️ Local: {event.location}")
    city_country = ", ".join(part for part in (event.city, event.country) if part)
    if city_country:
        lines.append(f"🌎 Cidade/País: {city_country}")
    lines.append(f"ℹ️ Status: {event.status}")
    if event.source_url:
        lines.append(f"🔗 Fonte oficial: {event.source_url}")
    verified = event.last_verified.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    lines.append(f"🕒 Última verificação: {verified:%d/%m/%Y %H:%M %Z}")
    return "\n".join(lines)


def _ical_status(event: SportsEvent) -> str:
    if event.status == "POSTPONED":
        return "TENTATIVE"
    return event.status


def _to_vevent(event: SportsEvent) -> Event:
    component = Event()
    verified_utc = event.last_verified.astimezone(UTC)
    component.add("uid", permanent_uid(event))
    component.add("dtstamp", verified_utc)
    component.add("created", verified_utc)
    component.add("last-modified", verified_utc)
    component.add("sequence", event.sequence)

    output_zone = ZoneInfo(DEFAULT_TIMEZONE)
    if event.all_day:
        start_date = event.start.astimezone(output_zone).date()
        if event.end is None:
            end_date = start_date + timedelta(days=1)
        else:
            end_date = event.end.astimezone(output_zone).date()
            if end_date <= start_date:
                end_date = start_date + timedelta(days=1)
        component.add("dtstart", start_date)
        component.add("dtend", end_date)
    else:
        component.add("dtstart", event.start.astimezone(output_zone))
        component.add("dtend", event.end.astimezone(output_zone))

    component.add("summary", event.title)
    component.add("description", _description(event))
    if event.location:
        component.add("location", event.location)
    if event.source_url:
        component.add("url", event.source_url)
    component.add("status", _ical_status(event))
    categories = [value for value in (event.sport, event.category, event.color_group) if value]
    if categories:
        component.add("categories", categories)
    component.add("transp", "TRANSPARENT")
    return component


def build_calendar(events: list[SportsEvent], feed_key: str) -> bytes:
    title = FEED_METADATA[feed_key][0]
    calendar = Calendar()
    calendar.add("version", "2.0")
    calendar.add("prodid", PRODID)
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("X-WR-CALNAME", title)
    calendar.add("X-WR-TIMEZONE", DEFAULT_TIMEZONE)
    for event in sorted(events, key=lambda item: (item.start, item.title, permanent_uid(item))):
        calendar.add_component(_to_vevent(event))

    # icalendar folds long lines. Normalize once more to guarantee RFC-style CRLF.
    raw = calendar.to_ical()
    normalized_lines = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
    while normalized_lines and normalized_lines[-1] == b"":
        normalized_lines.pop()
    return b"\r\n".join(normalized_lines) + b"\r\n"


def generate_calendars(events: list[SportsEvent], docs_dir: Path) -> tuple[dict[str, int], list[Path]]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    feed_events: dict[str, list[SportsEvent]] = {key: [] for key in FEED_METADATA}
    feed_events["all"] = list(events)
    for event in events:
        feed_events[event.color_group].append(event)

    changed: list[Path] = []
    counts: dict[str, int] = {}
    for feed_key, selected in feed_events.items():
        path = docs_dir / f"{feed_key}.ics"
        if _write_bytes_if_changed(path, build_calendar(selected, feed_key)):
            changed.append(path)
        counts[feed_key] = len(selected)
    return counts, changed


def generate_index(counts: dict[str, int], generated_at: datetime, docs_dir: Path) -> bool:
    generated_local = generated_at.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    cards = []
    for feed_key, (name, purpose) in FEED_METADATA.items():
        filename = f"{feed_key}.ics"
        cards.append(
            f"""<article class="feed-card">
  <h2>{escape(name)}</h2>
  <p>{escape(purpose)}</p>
  <p class="count"><strong>{counts.get(feed_key, 0)}</strong> evento(s)</p>
  <div class="actions">
    <a href="{filename}">Abrir {escape(filename)}</a>
    <button type="button" data-feed="{filename}">Copiar link</button>
  </div>
</article>"""
        )

    cards_html = "\n".join(cards)

    page = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sports Calendar Hub — Calendários esportivos</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f3f6f9; color: #17202a; }}
    main {{ width: min(1080px, calc(100% - 2rem)); margin: 0 auto; padding: 3rem 0; }}
    header {{ background: #0b3d2e; color: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 10px 30px #0b3d2e33; }}
    h1 {{ margin-top: 0; font-size: clamp(2rem, 5vw, 3.6rem); line-height: 1.05; }}
    .notice {{ padding: 1rem; margin: 1.5rem 0; border-left: 5px solid #e67e22; background: #fff4e6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }}
    .feed-card {{ background: white; padding: 1.25rem; border-radius: .8rem; box-shadow: 0 3px 14px #22334416; }}
    .feed-card h2 {{ margin-top: 0; }}
    .count {{ color: #355; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: .6rem; }}
    a, button {{ border: 0; border-radius: .45rem; padding: .65rem .8rem; font: inherit; cursor: pointer; }}
    a {{ background: #0b6e4f; color: white; text-decoration: none; }}
    button {{ background: #dfe9e5; color: #123; }}
    footer {{ margin-top: 2rem; color: #52616b; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Sports Calendar Hub — Calendários esportivos</h1>
      <p>Feeds universais em iCalendar (ICS), gerados por Python e publicados automaticamente.</p>
    </header>
    <p class="notice"><strong>Versão inicial de demonstração.</strong> Todos os eventos atuais são fictícios e não constituem calendário oficial.</p>
    <section class="grid" aria-label="Feeds disponíveis">
{cards_html}
    </section>
    <footer>Última geração dos dados: <time datetime="{generated_local.isoformat()}">{generated_local:%d/%m/%Y às %H:%M %Z}</time>.</footer>
  </main>
  <script>
    document.querySelectorAll('[data-feed]').forEach((button) => {{
      button.addEventListener('click', async () => {{
        const url = new URL(button.dataset.feed, window.location.href).href;
        await navigator.clipboard.writeText(url);
        button.textContent = 'Link copiado';
      }});
    }});
  </script>
</body>
</html>
"""
    return _write_bytes_if_changed(docs_dir / "index.html", page.encode("utf-8"))
