"""Runner de crawl — fetch listado, parse, dedup, upsert Property.

No hardcodea credenciales. No entra detrás de login.
Logging por fuente para auditar caídas de selectores.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import requests

from .dedup import is_duplicate
from .normalize import to_property_payload
from .selectors import SOURCES, SourceConfig

logger = logging.getLogger("propomi.crawler")

# Antigüedad máxima al indexar (días) — doc maestro
MAX_AGE_DAYS = 90
USER_AGENT = "PropomiBot/0.1 (+https://propomi.lat; research)"


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    # USD 120.000 / U$S 120,000 / 120000
    m = re.search(r"([\d]+(?:[.,]\d{3})*(?:[.,]\d+)?)", text.replace(" ", ""))
    if not m:
        return None
    num = m.group(1).replace(".", "").replace(",", "")
    try:
        return float(num)
    except ValueError:
        return None


def fetch_list_html(source: SourceConfig, timeout: int = 20) -> str:
    url = urljoin(source.base_url, source.list_path)
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def parse_cards_naive(html: str, source: SourceConfig) -> list[dict[str, Any]]:
    """Parser mínimo por regex/CSS-ish — reemplazar con BeautifulSoup cuando se validen selectores.

    Extrae links y títulos aproximados; no depende de libs HTML pesadas.
    """
    items: list[dict[str, Any]] = []
    # hrefs relativos/absolutos al dominio de la fuente
    for m in re.finditer(r'href="([^"]+)"[^>]*>([^<]{10,120})', html, re.I):
        href, title = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if not href or "javascript" in href:
            continue
        if source.id == "zonaprop" and "/propiedades/" not in href and "/departamento" not in href:
            continue
        if source.id == "argenprop" and "/departamento" not in href and "/propiedad" not in href:
            continue
        full = urljoin(source.base_url, href)
        items.append({
            "title": title[:180],
            "url": full,
            "source_url": full,
            "zone": "Caballito",
            "city": "Buenos Aires",
            "type": "departamento",
            "price": None,
            "images": [],
            "description": "",
        })
        if len(items) >= 40:
            break
    return items


def upsert_properties(db, items: list[dict[str, Any]], source_id: str) -> dict[str, int]:
    """Upsert hacia el modelo Property de main. Requiere Session abierta."""
    from app.main import Property, MAX_PROPERTY_IMAGES

    seen: set[str] = set()
    created = updated = skipped = 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)

    for raw in items:
        if is_duplicate(raw, seen):
            skipped += 1
            continue
        payload = to_property_payload(raw, source_id)
        # Si hay origin_published_at parseable y es viejo, skip
        # (string libre del portal — best effort)
        existing = None
        src_url = payload.get("source_url") or ""
        if src_url:
            from sqlalchemy import select as sa_select
            existing = db.scalar(sa_select(Property).where(Property.source_url == src_url))
        if existing:
            existing.title = payload["title"]
            existing.price = payload["price"] or existing.price
            existing.description = payload["description"] or existing.description
            if payload["images"]:
                existing.images = payload["images"][:MAX_PROPERTY_IMAGES]
                existing.image = payload["images"][0]
            existing.last_seen_at = now
            updated += 1
        else:
            prop = Property(
                id=f"c-{uuid.uuid4().hex[:12]}",
                title=payload["title"],
                type=payload["type"],
                operation="Venta",
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
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def run_crawl(db, source_ids: list[str] | None = None) -> dict[str, Any]:
    """Ejecuta crawl de las fuentes indicadas (default: todas)."""
    ids = source_ids or list(SOURCES.keys())
    report: dict[str, Any] = {"sources": {}, "ok": True}
    for sid in ids:
        source = SOURCES.get(sid)
        if not source:
            report["sources"][sid] = {"error": "unknown source"}
            report["ok"] = False
            continue
        try:
            html = fetch_list_html(source)
            items = parse_cards_naive(html, source)
            stats = upsert_properties(db, items, sid)
            report["sources"][sid] = {"fetched": len(items), **stats}
            logger.info("crawler source=%s fetched=%s stats=%s", sid, len(items), stats)
        except Exception as exc:
            logger.exception("crawler source=%s failed", sid)
            report["sources"][sid] = {"error": str(exc)}
            report["ok"] = False
    return report
