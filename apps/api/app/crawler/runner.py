"""Runner de crawl — dos etapas por fuente:

  1) listado: generar URLs de listado (selectors.SOURCES[...].list_urls_fn)
     y extraer de su HTML las URLs de fichas individuales (links.py).
  2) detalle: para cada URL de ficha, bajar el HTML y parsearlo con el
     parser específico de la fuente (parsers.parse_by_source), normalizar
     (normalize.to_property_payload) y hacer upsert contra Property.

No hardcodea credenciales. No entra detrás de login. No crawlea fuentes
con `enabled=False` en selectors.py (pendientes de confirmar robots.txt).
Logging por fuente para auditar caídas de selectores/parsers.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .dedup import is_duplicate
from .links import extract_detail_urls
from .normalize import to_property_payload
from .parsers import parse_by_source
from .selectors import SOURCES, SourceConfig

logger = logging.getLogger("propomi.crawler")

MAX_AGE_DAYS = 90
USER_AGENT = "PropomiBot/0.1 (+https://propomi.lat; research)"

# Límites de cortesía — evitar hammering de portales de terceros y del
# propio dyno free de Render. Ajustar cuando haya cron real + colas.
MAX_LIST_PAGES_PER_SOURCE = 3
MAX_DETAILS_PER_SOURCE = 15
REQUEST_DELAY_SECONDS = 1.0


def _get(url: str, timeout: int = 20) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def discover_detail_urls(source: SourceConfig) -> list[str]:
    """Etapa 1: recorre listados y junta URLs de fichas, sin duplicados."""
    urls: list[str] = []
    seen: set[str] = set()
    pages_fetched = 0
    for list_url in source.list_urls_fn():
        if pages_fetched >= MAX_LIST_PAGES_PER_SOURCE:
            break
        try:
            html = _get(list_url)
        except Exception:
            logger.exception("crawler source=%s listado fallido url=%s", source.id, list_url)
            continue
        pages_fetched += 1
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            found = extract_detail_urls(source.id, html, source.base_url, limit=MAX_DETAILS_PER_SOURCE)
        except KeyError:
            logger.warning("crawler source=%s sin extractor de links", source.id)
            break
        for u in found:
            if u not in seen:
                seen.add(u)
                urls.append(u)
        if len(urls) >= MAX_DETAILS_PER_SOURCE:
            break
    return urls[:MAX_DETAILS_PER_SOURCE]


def upsert_payload(db, payload: dict[str, Any], source_id: str) -> str:
    """Upsert de un único payload ya normalizado. Devuelve 'created'|'updated'|'skipped'."""
    from app.main import Property, MAX_PROPERTY_IMAGES
    from sqlalchemy import select as sa_select

    src_url = payload.get("source_url") or ""
    existing = None
    if src_url:
        existing = db.scalar(sa_select(Property).where(Property.source_url == src_url))

    now = datetime.now(timezone.utc)
    if existing:
        existing.title = payload["title"]
        existing.price = payload["price"] or existing.price
        existing.description = payload["description"] or existing.description
        if payload["images"]:
            existing.images = payload["images"][:MAX_PROPERTY_IMAGES]
            existing.image = payload["images"][0]
        existing.last_seen_at = now
        return "updated"

    prop = Property(
        id=f"c-{uuid.uuid4().hex[:12]}",
        title=payload["title"],
        type=payload["type"],
        operation=payload["operation"],
        price=payload["price"] or 0,
        currency=payload["currency"],
        zone=payload["zone"],
        city=payload["city"],
        surface=payload.get("surface") or 0,
        rooms=payload.get("rooms") or 0,
        bedrooms=payload.get("bedrooms") or 0,
        bathrooms=payload.get("bathrooms") or 0,
        images=payload.get("images") or [],
        image=payload.get("image") or "",
        description=payload.get("description") or "",
        source=source_id,
        source_url=src_url or f"crawler://{source_id}/{uuid.uuid4().hex[:8]}",
        freshness="crawler",
        origin_published_at=payload.get("origin_published_at"),
        agency_id=None,
        detected_at=now,
        last_seen_at=now,
    )
    db.add(prop)
    return "created"


def run_source(db, source: SourceConfig) -> dict[str, Any]:
    detail_urls = discover_detail_urls(source)
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
    seen_fp: set[str] = set()

    for url in detail_urls:
        try:
            html = _get(url)
        except Exception:
            logger.exception("crawler source=%s detalle fallido url=%s", source.id, url)
            stats["errors"] += 1
            continue
        time.sleep(REQUEST_DELAY_SECONDS)

        try:
            raw = parse_by_source(source.id, html, url)
        except Exception:
            logger.exception("crawler source=%s parser falló url=%s", source.id, url)
            stats["errors"] += 1
            continue
        if not raw:
            stats["errors"] += 1
            continue

        payload = to_property_payload(raw)
        if is_duplicate(payload, seen_fp):
            stats["skipped"] += 1
            continue

        result = upsert_payload(db, payload, source.id)
        stats[result] += 1

    db.commit()
    return {"discovered": len(detail_urls), **stats}


def run_crawl(db, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Ejecuta crawl de las fuentes indicadas (default: todas las habilitadas)."""
    ids = source_ids or [sid for sid, s in SOURCES.items() if s.enabled]
    report: dict[str, Any] = {"sources": {}, "ok": True}

    for sid in ids:
        source = SOURCES.get(sid)
        if not source:
            report["sources"][sid] = {"error": "unknown source"}
            report["ok"] = False
            continue
        if not source.enabled:
            report["sources"][sid] = {"skipped": True, "reason": source.robots_note or "disabled"}
            continue
        try:
            stats = run_source(db, source)
            report["sources"][sid] = stats
            logger.info("crawler source=%s stats=%s", sid, stats)
        except Exception as exc:
            logger.exception("crawler source=%s failed", sid)
            report["sources"][sid] = {"error": str(exc)}
            report["ok"] = False

    return report
