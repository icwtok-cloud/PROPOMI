"""Normalización RawListing (o dict) → payload Property Propomi."""
from __future__ import annotations

import re
from typing import Any

from .base import RawListing

MAX_IMAGES = 5


def strip_description(text: str | None) -> str:
    """Segunda pasada de sanitización, reusando el sanitizer canónico de
    main.py (ya usado en /leads, /offers, etc.) para que todo el sitio
    tenga un único criterio de qué se considera 'dato de contacto'.
    Los parsers de fichas (parsers/*.py) ya hacen una primera pasada con
    base.strip_contact_leaks al momento de extraer del HTML; esto es
    defensa en profundidad, no reemplaza esa primera limpieza.
    """
    if not text:
        return ""
    try:
        from app.main import strip_contact_leaks
        return strip_contact_leaks(text)
    except Exception:
        patterns = [
            re.compile(r"(\+?54)?[\s\-\.]?9?[\s\-\.]?\(?\d{2,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}"),
            re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            re.compile(r"https?://|www\.", re.I),
        ]
        out = text
        for p in patterns:
            out = p.sub("[dato de contacto oculto]", out)
        return out


def to_property_payload(raw: RawListing | dict[str, Any], source_id: str | None = None) -> dict[str, Any]:
    """Acepta un RawListing (flujo nuevo: parse_detail de fichas) o un dict
    (flujo viejo: cards de listado, por compatibilidad). `source_id` es
    opcional cuando raw ya trae `.source` / `["source"]`.
    """
    if isinstance(raw, RawListing):
        d = raw.__dict__
    else:
        d = raw

    images = d.get("images") or []
    if isinstance(images, str):
        images = [images]
    images = [u for u in images if u][:MAX_IMAGES]

    return {
        "title": (d.get("title") or "Sin título")[:180],
        "type": d.get("property_type") or d.get("type") or "Departamento",
        "operation": d.get("operation") or "Venta",
        "price": float(d.get("price") or 0),
        "currency": d.get("currency") or "USD",
        "zone": d.get("zone") or "",
        "city": d.get("city") or "",
        "surface": d.get("surface") or d.get("surface_covered") or 0,
        "rooms": d.get("rooms") or d.get("bedrooms") or 0,
        "bedrooms": d.get("bedrooms") or 0,
        "bathrooms": d.get("bathrooms") or 0,
        "parking": bool(d.get("parking")),
        "credit": bool(d.get("credit")),
        "images": images,
        "image": images[0] if images else "",
        "description": strip_description(d.get("description")),
        "source": d.get("source") or source_id,
        "source_url": d.get("source_url") or d.get("url") or "",
        "origin_published_at": d.get("origin_published_at"),
        "freshness": d.get("freshness") or "crawler",
        # Nunca copiar el teléfono del portal a la ficha pública de Propomi
        # (regla ya acordada: la verificación de identidad es SMS propio).
        "contact_phone_raw": None,
        "agency_hint": d.get("agency_name") or None,
        "external_id": d.get("external_id"),
    }
