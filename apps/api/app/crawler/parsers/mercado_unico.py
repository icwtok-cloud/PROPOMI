"""Mercado Único (Santa Fe) — window.__NUXT__ embebido."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "mercado_unico"


def _extract_nuxt_payload(html: str) -> dict[str, Any] | None:
    """Nuxt comprime el state en una IIFE; intentamos JSON directo o heurística."""
    m = re.search(r"window\.__NUXT__\s*=\s*(.*?);\s*</script>", html, re.S)
    if not m:
        return None
    raw = m.group(1).strip()
    # Caso simple: objeto JSON
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    # IIFE: buscar bloque propiedad en data
    # Fallback: parsear campos visibles + regex de IDs
    return {"_raw": raw}


def parse_detail(html: str, url: str) -> RawListing | None:
    # Preferir datos del state NUXT si se puede evaluar estructura conocida
    # En HTML de muestra: precio 95000 USD, 3 dorm, dirección en og:title
    title_m = re.search(r"<title>([^|<]+)", html)
    title = (title_m.group(1).strip() if title_m else "")[:180]

    # og:description
    desc_m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    # Precio en NUXT: normalizadoUSD o visible
    price = None
    for pat in [
        r'normalizadoUSD["\']?\s*:\s*(\d+)',
        r'"valor"\s*:\s*(\d{4,})',
        r"USD\s*([\d.]+)",
    ]:
        pm = re.search(pat, html)
        if pm:
            price = parse_price(pm.group(1))
            if price and price > 1000:
                break

    bedrooms = first_int(
        *(m.group(1) for m in re.finditer(r"dormitorios[\"']?\s*:\s*(\d+)", html, re.I))
    )
    bathrooms = first_int(
        *(m.group(1) for m in re.finditer(r"banos[\"']?\s*:\s*(\d+)", html, re.I))
    )
    surface = None
    sm = re.search(r"superficieCubierta[\"']?\s*:\s*([\d.]+)", html)
    if sm:
        surface = parse_price(sm.group(1))

    images = re.findall(r"https://images\.mercado-unico\.com/[^\"'\\]+", html)
    # dedupe preserve order
    seen = set()
    imgs = []
    for u in images:
        u = u.replace("\\u002F", "/")
        if u not in seen and "c_thumb" not in u:
            seen.add(u)
            imgs.append(u)
        if len(imgs) >= 5:
            break

    addr_m = re.search(r'direccion[\"\']?\s*:\s*[\"\']([^\"\']+)', html)
    address = addr_m.group(1) if addr_m else ""
    barrio_m = re.search(r'nombre[\"\']?\s*:\s*[\"\'](La Esmeralda|[^\"\']+)[\"\'].*?slug[\"\']?\s*:\s*[\"\']la-esmeralda', html, re.S)
    zone = ""
    # barrio.nombre en payload NUXT (puede venir sin comillas en IIFE)
    zm = re.search(r'barrio:\{[^}]*nombre:"([^"]+)"', html)
    if not zm:
        zm = re.search(r'barrio:\{[^}]*nombre:"([^"]+)"', html)
    if not zm:
        zm = re.search(r'nombre:"([A-Za-zÁÉÍÓÚáéíóúñÑ ]+)",provincia:[a-z],slug:"[a-z-]+",ciudad:', html)
    if zm:
        zone = zm.group(1)
    if not zone:
        om = re.search(r'og:title"[^>]+content="[^"]*,\s*([^,]+),\s*Santa Fe"', html)
        if om:
            zone = om.group(1).strip()

    agency_m = re.search(r'(LOQUET Inmobiliaria|[\w\s]+Inmobiliaria)', html)
    phone_m = re.search(r"Tel:\s*(\d+)", html)
    external = None
    em = re.search(r"/propiedades/([a-f0-9]{24})", url)
    if em:
        external = em.group(1)

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title or address,
        description=description,
        price=price,
        currency="USD",
        zone=zone,
        city="Santa Fe",
        province="Santa Fe",
        address=address,
        surface=surface,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        rooms=bedrooms,
        property_type="Casa",
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=imgs,
        agency_name=agency_m.group(1) if agency_m else "",
        agency_phone=phone_m.group(1) if phone_m else "",
    )
