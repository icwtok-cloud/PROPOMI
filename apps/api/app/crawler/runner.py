"""Runner de crawl — dos etapas por fuente:

  1) listado: generar URLs de listado (selectors.SOURCES[...].list_urls_fn)
     y extraer de su HTML las URLs de fichas individuales (links.py).
  2) detalle: para cada URL de ficha, bajar el HTML y parsearlo con el
     parser específico de la fuente (parsers.parse_by_source), normalizar
     (normalize.to_property_payload) y hacer upsert contra Property.

No hardcodea credenciales. No entra detrás de login. No crawlea fuentes
con `enabled=False` en selectors.py (pendientes de confirmar robots.txt).
Logging por fuente para auditar caídas de selectores/parsers.

Paginación con estado (CrawlCursor): arranca desde last_page+1 y persiste
el avance; al llegar al tope de la fuente reinicia a 1 (upsert idempotente).
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

MAX_AGE_DAYS = 60
USER_AGENT = "PropomiBot/0.1 (+https://propomi.lat; research)"

# Límites de cortesía — evitar hammering de portales de terceros y del
# propio dyno free de Render. Ajustar cuando haya cron real + colas.
MAX_LIST_PAGES_PER_SOURCE = 5
MAX_DETAILS_PER_SOURCE = 80
REQUEST_DELAY_SECONDS = 1.0

# Tope de paginación por fuente (robots.txt / cortesía). Al llegar se reinicia.
SOURCE_MAX_PAGE: dict[str, int] = {
    "zonaprop": 5,  # robots.txt: solo páginas 1-5
    "argenprop": 5,
    "cordobaprop": 10,
    "inmoup": 5,
}


def _get(url: str, timeout: int = 20) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"},
        timeout=timeout,
    )
    resp.raise_for_status()
    # Preferir UTF-8 real del body (muchos portales no declaran charset y
    # requests asume ISO-8859-1 → mojibake). Si UTF-8 falla, apparent_encoding.
    raw = resp.content
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        enc = resp.apparent_encoding or resp.encoding or "utf-8"
        if enc and enc.lower() in ("iso-8859-1", "latin-1", "windows-1252"):
            # reintentar utf-8 con replace solo si apparent también es latin
            try:
                return raw.decode("utf-8", errors="replace")
            except Exception:
                pass
        try:
            return raw.decode(enc, errors="replace")
        except Exception:
            return raw.decode("utf-8", errors="replace")


def _get_or_create_cursor(db, source_id: str):
    from app.main import CrawlCursor
    cursor = db.get(CrawlCursor, source_id)
    if cursor is None:
        cursor = CrawlCursor(source_id=source_id, last_page=0, total_seen=0)
        db.add(cursor)
        db.flush()
    return cursor


def discover_detail_urls(source: SourceConfig, db=None) -> list[str]:
    """Etapa 1: recorre listados y junta URLs de fichas, sin duplicados.

    Si se pasa `db`, usa CrawlCursor para arrancar desde last_page+1 y
    persistir el avance al terminar (reinicia al tope de la fuente).
    """
    urls: list[str] = []
    seen: set[str] = set()
    pages_fetched = 0

    all_list_urls = list(source.list_urls_fn())
    start_idx = 0
    cursor = None
    max_page = SOURCE_MAX_PAGE.get(source.id, len(all_list_urls) or 1)

    if db is not None:
        cursor = _get_or_create_cursor(db, source.id)
        # last_page es 1-based respecto de las páginas de la fuente; 0 = nunca corrió
        if cursor.last_page > 0:
            # Avanzar al siguiente bloque de páginas
            start_idx = min(cursor.last_page, len(all_list_urls))
            if start_idx >= len(all_list_urls) or cursor.last_page >= max_page:
                # Tope alcanzado → reiniciar a 1
                start_idx = 0
                cursor.last_page = 0

    list_slice = all_list_urls[start_idx:]
    pages_this_run = 0
    absolute_page = start_idx  # 0-based index in all_list_urls

    for list_url in list_slice:
        if pages_fetched >= MAX_LIST_PAGES_PER_SOURCE:
            break
        try:
            html = _get(list_url)
        except Exception:
            logger.exception("crawler source=%s listado fallido url=%s", source.id, list_url)
            absolute_page += 1
            continue
        pages_fetched += 1
        pages_this_run += 1
        absolute_page += 1
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

    if cursor is not None:
        # Persist advance: last_page is the absolute 1-based page we reached
        new_last = absolute_page
        if new_last >= max_page:
            new_last = 0  # reinicia en la próxima corrida
        cursor.last_page = new_last
        cursor.last_run_at = datetime.now(timezone.utc)
        cursor.total_seen = (cursor.total_seen or 0) + len(urls)
        db.flush()

    return urls[:MAX_DETAILS_PER_SOURCE]


def upsert_payload(db, payload: dict[str, Any], source_id: str) -> str:
    """Upsert de un único payload ya normalizado. Devuelve 'created'|'updated'|'skipped'."""
    from app.main import Property, MAX_PROPERTY_IMAGES, match_demand_requests_for_property
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
        # Bug encontrado 2026-09-14: antes esta rama solo tocaba title/price/
        # description/images, así que una vez creado un registro, zone/city/
        # type/etc. quedaban congelados para siempre — un re-crawl nunca
        # podía corregir datos malos (ej. el mojibake de encoding) ni
        # reflejar cambios reales del portal de origen.
        existing.type = payload["type"] or existing.type
        existing.operation = payload["operation"] or existing.operation
        existing.currency = payload["currency"] or existing.currency
        existing.zone = payload["zone"] or existing.zone
        existing.city = payload["city"] or existing.city
        if payload.get("country"):
            existing.country = payload["country"]
        if payload.get("province") is not None:
            existing.province = payload.get("province") or existing.province or ""
        if payload.get("surface"):
            existing.surface = payload["surface"]
        if payload.get("rooms"):
            existing.rooms = payload["rooms"]
        if payload.get("bedrooms"):
            existing.bedrooms = payload["bedrooms"]
        if payload.get("bathrooms"):
            existing.bathrooms = payload["bathrooms"]
        if payload["images"]:
            existing.images = payload["images"][:MAX_PROPERTY_IMAGES]
            existing.image = payload["images"][0]
        existing.last_seen_at = now
        # Si el aviso reaparece en el portal, re-mostrar (plan maestro secc. 7)
        existing.hidden_at = None
        if payload.get("priority_score") is not None:
            existing.priority_score = float(payload["priority_score"])
        if payload.get("origin_published_at"):
            existing.origin_published_at = payload["origin_published_at"]
        match_demand_requests_for_property(db, existing)
        return "updated"

    from app.main import normalize_phone
    from .dedup import find_cross_source_match
    phone_raw = payload.get("contact_phone_raw") or None
    phone_norm = normalize_phone(phone_raw) if phone_raw else None

    group_id = None
    twin = find_cross_source_match(db, payload, source_id)
    if twin is not None:
        group_id = twin.listing_group_id or f"lg-{uuid.uuid4().hex[:12]}"
        if not twin.listing_group_id:
            twin.listing_group_id = group_id

    prop = Property(
        id=f"c-{uuid.uuid4().hex[:12]}",
        title=payload["title"],
        type=payload["type"],
        operation=payload["operation"],
        price=payload["price"] or 0,
        currency=payload["currency"],
        zone=payload["zone"],
        city=payload["city"],
        country=payload.get("country") or "Argentina",
        province=payload.get("province") or "",
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
        contact_phone_raw=phone_raw,
        contact_phone_normalized=phone_norm,
        listing_group_id=group_id,
        detected_at=now,
        last_seen_at=now,
        hidden_at=None,
        priority_score=float(payload.get("priority_score") or 0),
    )
    db.add(prop)
    db.flush()
    match_demand_requests_for_property(db, prop)
    return "created"


def run_source(db, source: SourceConfig) -> dict[str, Any]:
    detail_urls = discover_detail_urls(source, db=db)
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


def run_crawl(
    db,
    source_ids: list[str] | None = None,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """Ejecuta crawl de las fuentes indicadas (default: habilitadas por prioridad).

    Sin source_ids (cron/automático): orden vía compute_source_priority(db).
    Con source_ids explícito (admin): se respeta el orden del caller sin reordenar.

    on_progress(opcional): callable(dict) con estado parcial
      {phase, current_source, completed_sources, sources, ok}.
    """
    if source_ids is not None:
        ids = list(source_ids)
    else:
        try:
            from .crawl_queue_priority import compute_source_priority
            ids = compute_source_priority(db)
        except Exception:
            logger.exception("crawl_queue_priority failed; fallback a orden SOURCES")
            ids = [sid for sid, s in SOURCES.items() if s.enabled]
    report: dict[str, Any] = {"sources": {}, "ok": True, "planned_sources": list(ids)}
    completed: list[str] = []

    def _emit(phase: str, current: str | None = None) -> None:
        if not on_progress:
            return
        try:
            on_progress({
                "phase": phase,
                "current_source": current,
                "completed_sources": list(completed),
                "planned_sources": list(ids),
                "sources": dict(report["sources"]),
                "ok": report["ok"],
            })
        except Exception:
            logger.exception("on_progress callback failed")

    _emit("started", None)
    for sid in ids:
        source = SOURCES.get(sid)
        if not source:
            report["sources"][sid] = {"error": "unknown source"}
            report["ok"] = False
            completed.append(sid)
            _emit("source_done", sid)
            continue
        if not source.enabled:
            report["sources"][sid] = {"skipped": True, "reason": source.robots_note or "disabled"}
            completed.append(sid)
            _emit("source_done", sid)
            continue
        _emit("source_start", sid)
        try:
            stats = run_source(db, source)
            report["sources"][sid] = stats
            logger.info("crawler source=%s stats=%s", sid, stats)
        except Exception as exc:
            logger.exception("crawler source=%s failed", sid)
            report["sources"][sid] = {"error": str(exc)}
            report["ok"] = False
        completed.append(sid)
        _emit("source_done", sid)

    logger.info("crawler report=%s", report)
    _emit("finished", None)
    return report
