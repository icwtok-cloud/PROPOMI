"""Prioridad de cola de crawleo entre fuentes enabled (roadmap §5.5).

Ordena qué fuentes conviene crawlear primero cuando `run_crawl(db)` se
invoca sin `source_ids` (cron / corrida automática).

Fórmula (score más alto = primero en la cola)
--------------------------------------------
    score(source) = AGE_WEIGHT * age_hours
                  + DEMAND_WEIGHT * demand_hits

* age_hours: horas desde CrawlCursor.last_run_at. Si no hay cursor (nunca
  crawleada), se usa NEVER_CRAWLED_AGE_HOURS (~1 año) para ponerla primero.
* demand_hits: cantidad de DemandRequest activos cuya zone/city aparece en
  al menos una Property ya indexada de esa fuente (`Property.source == id`).
  No inventamos un mapa fuente→zona estático: usamos el inventario real
  como proxy de cobertura geográfica. Fuentes sin inventario aún no reciben
  boost de demanda (la antigüedad las prioriza igual).

Fuera de alcance (no hay señal en schema): tasa de error reciente por fuente.
CrawlCursor solo tiene last_page / last_run_at / total_seen — no se agrega
campo nuevo en este módulo.

Esto NO altera Property.priority_score (orden de listado al comprador);
solo el orden de ejecución de fuentes en el crawler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from .selectors import SOURCES

logger = logging.getLogger("propomi.crawler.priority")

# Equivalencias: 1 demanda matcheada ≈ 24 h de antigüedad de crawl.
AGE_WEIGHT = 1.0
DEMAND_WEIGHT = 24.0
NEVER_CRAWLED_AGE_HOURS = 365.0 * 24.0


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _age_hours(last_run_at: datetime | None, now: datetime) -> float:
    if last_run_at is None:
        return NEVER_CRAWLED_AGE_HOURS
    last = _aware(last_run_at)
    if last is None:
        return NEVER_CRAWLED_AGE_HOURS
    delta = (now - last).total_seconds() / 3600.0
    return max(0.0, delta)


def _active_demand_zones_cities(db) -> tuple[set[str], set[str]]:
    """Zonas y ciudades de DemandRequest.active=True y no vencidos."""
    from app.main import DemandRequest

    now = datetime.now(timezone.utc)
    rows = db.scalars(select(DemandRequest).where(DemandRequest.active == True)).all()  # noqa: E712
    zones: set[str] = set()
    cities: set[str] = set()
    for dr in rows:
        exp = _aware(dr.expires_at)
        if exp is not None and exp < now:
            continue
        if dr.zone:
            zones.add(dr.zone.strip().lower())
        # DemandRequest no tiene city propia; zone a veces es ciudad.
        if dr.zone:
            cities.add(dr.zone.strip().lower())
    return zones, cities


def _demand_hits_for_source(db, source_id: str, demand_zones: set[str], demand_cities: set[str]) -> int:
    """Cuántas demandas activas 'tocan' el inventario actual de la fuente."""
    if not demand_zones and not demand_cities:
        return 0
    from app.main import Property

    rows = db.execute(
        select(Property.zone, Property.city).where(Property.source == source_id)
    ).all()
    if not rows:
        return 0
    source_zones = {(z or "").strip().lower() for z, c in rows if z}
    source_cities = {(c or "").strip().lower() for z, c in rows if c}
    hits = 0
    for z in demand_zones:
        if z in source_zones or z in source_cities:
            hits += 1
    # Evitar doble conteo si zone==city label ya contado
    for c in demand_cities:
        if c in demand_zones:
            continue
        if c in source_zones or c in source_cities:
            hits += 1
    return hits


def compute_source_scores(db, now: datetime | None = None) -> list[tuple[str, float, dict[str, Any]]]:
    """Devuelve [(source_id, score, detail), ...] ordenado score desc."""
    from app.main import CrawlCursor

    now = now or datetime.now(timezone.utc)
    demand_zones, demand_cities = _active_demand_zones_cities(db)
    scored: list[tuple[str, float, dict[str, Any]]] = []

    for sid, cfg in SOURCES.items():
        if not cfg.enabled:
            continue
        cursor = db.get(CrawlCursor, sid)
        last_run = cursor.last_run_at if cursor else None
        age = _age_hours(last_run, now)
        demand = _demand_hits_for_source(db, sid, demand_zones, demand_cities)
        score = AGE_WEIGHT * age + DEMAND_WEIGHT * demand
        detail = {
            "age_hours": round(age, 2),
            "demand_hits": demand,
            "last_run_at": last_run.isoformat() if last_run else None,
            "score": round(score, 2),
        }
        scored.append((sid, score, detail))

    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def compute_source_priority(db) -> list[str]:
    """source.id enabled ordenados de mayor a menor prioridad de crawleo."""
    scored = compute_source_scores(db)
    ordered = [sid for sid, _, _ in scored]
    logger.info(
        "crawl_queue_priority order=%s details=%s",
        ordered,
        {sid: d for sid, _, d in scored},
    )
    return ordered
