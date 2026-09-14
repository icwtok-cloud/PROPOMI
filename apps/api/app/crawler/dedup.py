"""Dedup por dirección aproximada + precio + m2."""
from __future__ import annotations

from typing import Any


def fingerprint(item: dict[str, Any]) -> str:
    zone = (item.get("zone") or "").strip().lower()
    title = (item.get("title") or "").strip().lower()[:80]
    price = item.get("price") or 0
    surface = item.get("surface") or 0
    # redondeo grueso de precio/superficie para fusionar anuncios casi iguales
    price_bucket = int(float(price) // 5000) * 5000 if price else 0
    surface_bucket = int(float(surface) // 5) * 5 if surface else 0
    return f"{zone}|{price_bucket}|{surface_bucket}|{title[:40]}"


def is_duplicate(item: dict[str, Any], seen: set[str]) -> bool:
    fp = fingerprint(item)
    if fp in seen:
        return True
    seen.add(fp)
    return False
