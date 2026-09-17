"""Dedup por ubicación + precio + m2 + ambientes (+ país).

Fingerprint para fusionar el mismo aviso en 2+ portales (y dentro de una fuente).
Buckets de precio/superficie absorben diferencias menores de publicación.
"""
from __future__ import annotations

import re
from typing import Any


def _norm_addr(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s[:80]


def fingerprint(item: dict[str, Any]) -> str:
    country = (item.get("country") or "Argentina").strip().lower()
    city = (item.get("city") or "").strip().lower()
    zone = (item.get("zone") or "").strip().lower()
    addr = _norm_addr(item.get("address") or item.get("title") or "")
    price = item.get("price") or 0
    surface = item.get("surface") or 0
    # bucket más fino que antes (2.5k USD / 3 m²) para menos falsos positivos
    price_b = int(float(price) // 2500) * 2500 if price else 0
    surface_b = int(float(surface) // 3) * 3 if surface else 0
    rooms = item.get("rooms") or item.get("bedrooms") or 0
    ptype = (item.get("type") or item.get("property_type") or "").strip().lower()[:20]
    return f"{country}|{city}|{zone}|{addr}|{price_b}|{surface_b}|{rooms}|{ptype}"


def is_duplicate(item: dict[str, Any], seen: set[str]) -> bool:
    fp = fingerprint(item)
    if fp in seen:
        return True
    seen.add(fp)
    return False


def find_cross_source_match(db, payload: dict[str, Any], source_id: str):
    """Busca Property de OTRA fuente con mismo fingerprint aproximado (listing_group).

    Best-effort: city + price bucket + rooms + type; no re-crawlea.
    """
    from sqlalchemy import select
    from app.main import Property

    city = (payload.get("city") or "").strip()
    if not city:
        return None
    price = float(payload.get("price") or 0)
    rooms = int(payload.get("rooms") or payload.get("bedrooms") or 0)
    ptype = (payload.get("type") or "").strip()
    country = (payload.get("country") or "Argentina").strip()
    if not price:
        return None
    lo = price * 0.92
    hi = price * 1.08
    stmt = (
        select(Property)
        .where(Property.city == city)
        .where(Property.country == country)
        .where(Property.price >= lo)
        .where(Property.price <= hi)
        .where(Property.source != source_id)
        .where(Property.hidden_at.is_(None))
        .limit(30)
    )
    if rooms:
        stmt = stmt.where(Property.rooms == rooms)
    if ptype:
        stmt = stmt.where(Property.type == ptype)
    candidates = list(db.scalars(stmt).all())
    if not candidates:
        return None
    # prefer same zone
    zone = (payload.get("zone") or "").strip().lower()
    if zone:
        zmatch = [c for c in candidates if (c.zone or "").strip().lower() == zone]
        if zmatch:
            return zmatch[0]
    return candidates[0]
