"""Normalización RawListing (o dict) → payload Property Propomi."""
from __future__ import annotations

import re
from typing import Any

from .base import RawListing

MAX_IMAGES = 5

# País canónico por source_id (crawler). Override si RawListing.extras["country"].
SOURCE_COUNTRY: dict[str, str] = {
    "cordobaprop": "Argentina",
    "mendozaprop": "Argentina",
    "mercado_unico": "Argentina",
    "mercadolibre": "Argentina",
    "inmoup": "Argentina",
    "inmoclick": "Argentina",
    "icasas": "Argentina",
    "bienesonline": "Argentina",
    "infocasas_py": "Paraguay",
    "infocasas_uy": "Uruguay",
    "zonaprop": "Argentina",
    "argenprop": "Argentina",
    "properati": "Argentina",
}


def fix_mojibake(text: str | None) -> str:
    """Repara double-encoding típico UTF-8 leído como Latin-1 (CÃ³rdoba → Córdoba).

    Idempotente: si el texto ya es UTF-8 válido sin mojibake, no cambia.
    """
    if not text or not isinstance(text, str):
        return text or ""
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        # Solo aceptar si mejoró (menos secuencias típicas de mojibake)
        if fixed.count("Ã") < text.count("Ã"):
            return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return text



# --- Priority score (encargo #2, default reversible) ---
# Fórmula (pesos suman ~1.0; score final 0–100 aprox.):
#   recencia (0–40): origin_published_at ISO reciente o, si no hay, score medio
#   precio vs mediana zona+tipo (0–25): precio <= mediana → más puntos
#   tipología 2–3 amb / superficie media (0–20)
#   fotos >= 3 (0–15)
# No inventa datos: si falta una señal, esa componente aporta 0.
# El dueño del producto puede retocar pesos sin tocar el resto del pipeline.


def compute_priority_score(payload: dict, zone_median_price: float | None = None) -> float:
    """Calcula priority_score a partir del payload normalizado + mediana opcional."""
    from datetime import datetime, timezone, timedelta
    score = 0.0

    # 1) Recencia (hasta 40 pts)
    origin = payload.get("origin_published_at")
    recent = False
    if origin:
        try:
            s = str(origin).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
            if age_days <= 7:
                score += 40
                recent = True
            elif age_days <= 30:
                score += 25
            elif age_days <= 60:
                score += 10
        except (ValueError, TypeError):
            score += 15  # desconocido: puntaje neutro-bajo
    else:
        score += 15

    # 2) Precio vs mediana de zona+tipo (hasta 25)
    price = float(payload.get("price") or 0)
    if zone_median_price and zone_median_price > 0 and price > 0:
        ratio = price / zone_median_price
        if ratio <= 0.85:
            score += 25
        elif ratio <= 1.0:
            score += 18
        elif ratio <= 1.2:
            score += 8
        # muy por encima: 0
    elif price > 0:
        score += 10  # sin mediana, aporte neutro

    # 3) Tipología de alta rotación AR: 2–3 amb, superficie 40–90 m² (hasta 20)
    rooms = int(payload.get("rooms") or payload.get("bedrooms") or 0)
    surface = float(payload.get("surface") or 0)
    if rooms in (2, 3):
        score += 12
    elif rooms == 4:
        score += 6
    if 40 <= surface <= 90:
        score += 8
    elif 30 <= surface <= 120:
        score += 4

    # 4) Fotos suficientes (hasta 15)
    images = payload.get("images") or []
    n_img = len(images) if isinstance(images, list) else 0
    if n_img >= 5:
        score += 15
    elif n_img >= 3:
        score += 10
    elif n_img >= 1:
        score += 4

    return round(score, 2)



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

    sid = (d.get("source") or source_id or "") or ""
    extras = d.get("extras") or {}
    if not isinstance(extras, dict):
        extras = {}
    country = (
        extras.get("country")
        or d.get("country")
        or SOURCE_COUNTRY.get(sid)
        or "Argentina"
    )
    # normalizar códigos cortos
    _cmap = {"AR": "Argentina", "PY": "Paraguay", "UY": "Uruguay", "ar": "Argentina", "py": "Paraguay", "uy": "Uruguay"}
    country = _cmap.get(str(country), str(country))
    province = (d.get("province") or extras.get("province") or "")[:100]
    zone = fix_mojibake(d.get("zone") or "")
    city = fix_mojibake(d.get("city") or "")
    title = fix_mojibake((d.get("title") or "Sin título")[:180])
    description = fix_mojibake(strip_description(d.get("description")))

    return {
        "title": title,
        "type": d.get("property_type") or d.get("type") or "Departamento",
        "operation": d.get("operation") or "Venta",
        "price": float(d.get("price") or 0),
        "currency": d.get("currency") or "USD",
        "zone": zone,
        "city": city,
        "country": country,
        "province": province,
        "surface": d.get("surface") or d.get("surface_covered") or 0,
        "rooms": d.get("rooms") or d.get("bedrooms") or 0,
        "bedrooms": d.get("bedrooms") or 0,
        "bathrooms": d.get("bathrooms") or 0,
        "parking": bool(d.get("parking")),
        "credit": bool(d.get("credit")),
        "images": images,
        "image": images[0] if images else "",
        "description": description,
        "source": d.get("source") or source_id,
        "source_url": d.get("source_url") or d.get("url") or "",
        "origin_published_at": d.get("origin_published_at"),
        "freshness": d.get("freshness") or "crawler",
        # Nunca copiar el teléfono del portal a la ficha pública de Propomi
        # (regla ya acordada: la verificación de identidad es SMS propio).
        "contact_phone_raw": None,
        "agency_hint": d.get("agency_name") or None,
        "external_id": d.get("external_id"),
        "priority_score": compute_priority_score({
            "origin_published_at": d.get("origin_published_at"),
            "price": d.get("price"),
            "rooms": d.get("rooms") or d.get("bedrooms"),
            "bedrooms": d.get("bedrooms"),
            "surface": d.get("surface") or d.get("surface_covered"),
            "images": images,
        }),
    }
