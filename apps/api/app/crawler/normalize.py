"""Normalización + anti-fuga en descripción scrapeada."""
from __future__ import annotations

import re
from typing import Any

# Import perezoso del sanitizer del main para no ciclos en import-time
def strip_description(text: str | None) -> str:
    if not text:
        return ""
    try:
        from app.main import strip_contact_leaks
        return strip_contact_leaks(text)
    except Exception:
        # fallback mínimo si main no está cargado
        patterns = [
            re.compile(r"(\+?54)?[\s\-\.]?9?[\s\-\.]?\(?\d{2,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}"),
            re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            re.compile(r"https?://|www\.", re.I),
        ]
        out = text
        for p in patterns:
            out = p.sub("[dato de contacto oculto]", out)
        return out


def to_property_payload(raw: dict[str, Any], source_id: str) -> dict[str, Any]:
    images = raw.get("images") or []
    if isinstance(images, str):
        images = [images]
    images = [u for u in images if u][:5]
    return {
        "title": (raw.get("title") or "Sin título")[:180],
        "type": raw.get("type") or "departamento",
        "operation": "Venta",
        "price": float(raw.get("price") or 0),
        "currency": raw.get("currency") or "USD",
        "zone": raw.get("zone") or "Caballito",
        "city": raw.get("city") or "Buenos Aires",
        "surface": raw.get("surface"),
        "rooms": raw.get("rooms"),
        "bedrooms": raw.get("bedrooms"),
        "bathrooms": raw.get("bathrooms"),
        "images": images,
        "image": images[0] if images else "",
        "description": strip_description(raw.get("description")),
        "source": source_id,
        "source_url": raw.get("source_url") or raw.get("url") or "",
        "origin_published_at": raw.get("origin_published_at"),
        "freshness": raw.get("freshness") or "crawler",
    }
