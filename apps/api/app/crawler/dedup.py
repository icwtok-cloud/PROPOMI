"""Dedup por dirección aproximada + precio + m2 + ambientes.

Fingerprint pensado para fusionar el mismo aviso publicado en más de un
portal (ej. la misma propiedad en ZonaProp y Argenprop), no solo repetidos
dentro de una misma fuente.
"""
from __future__ import annotations

import re
from typing import Any


def _norm_addr(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s[:80]


def fingerprint(item: dict[str, Any]) -> str:
    zone = (item.get("zone") or item.get("city") or "").strip().lower()
    addr = _norm_addr(item.get("address") or item.get("title") or "")
    price = item.get("price") or 0
    surface = item.get("surface") or 0
    price_b = int(float(price) // 5000) * 5000 if price else 0
    surface_b = int(float(surface) // 5) * 5 if surface else 0
    rooms = item.get("rooms") or item.get("bedrooms") or 0
    return f"{zone}|{addr}|{price_b}|{surface_b}|{rooms}"


def is_duplicate(item: dict[str, Any], seen: set[str]) -> bool:
    fp = fingerprint(item)
    if fp in seen:
        return True
    seen.add(fp)
    return False
