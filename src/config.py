"""Project-wide constants and feed metadata."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
PRODID = "-//Sports Calendar Hub//PT-BR"
UID_DOMAIN = "sports-calendar-hub"

COLOR_GROUPS = (
    "sao-paulo",
    "selecao-brasileira",
    "clubes-regionais",
    "red-bull",
    "premier-league",
    "continentais",
    "automobilismo",
    "brasileirao",
    "olimpiadas-pan",
    "copas-do-mundo",
    "outros-esportes",
)

FEED_METADATA = {
    "all": (
        "Todos os eventos",
        "Calendário geral com todos os eventos normalizados.",
    ),
    "sao-paulo": (
        "São Paulo",
        "Jogos do São Paulo Futebol Clube, independentemente da competição.",
    ),
    "selecao-brasileira": (
        "Seleção Brasileira",
        "Jogos das seleções brasileiras, com prioridade sobre copas e torneios.",
    ),
    "clubes-regionais": (
        "Clubes regionais",
        "Jogos oficiais dos clubes regionais acompanhados, incluindo Botafogo-SP e Comercial-SP.",
    ),
    "red-bull": (
        "Red Bull",
        "Eventos de equipes Red Bull, RB Leipzig, RB Salzburg e Red Bull Bragantino.",
    ),
    "premier-league": (
        "Premier League",
        "Partidas da Premier League que não pertencem a um grupo prioritário.",
    ),
    "continentais": (
        "Competições continentais",
        "Libertadores, Sul-Americana, Champions League e competições continentais equivalentes.",
    ),
    "automobilismo": (
        "Automobilismo",
        "Corridas e etapas de categorias do automobilismo.",
    ),
    "brasileirao": (
        "Brasileirão",
        "Partidas do Campeonato Brasileiro que não pertencem a um grupo prioritário.",
    ),
    "olimpiadas-pan": (
        "Olimpíadas e Pan",
        "Eventos olímpicos e pan-americanos.",
    ),
    "copas-do-mundo": (
        "Copas do Mundo",
        "Eventos de Copas do Mundo que não pertencem a uma seleção prioritária.",
    ),
    "outros-esportes": (
        "Outros esportes",
        "Demais modalidades e competições não abrangidas pelos grupos anteriores.",
    ),
}

ALLOWED_STATUSES = {"CONFIRMED", "TENTATIVE", "POSTPONED", "CANCELLED"}
