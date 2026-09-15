"""Properati — pageData JS + meta; contacto por form (no scrapear teléfono de WA si se puede evitar)."""
from __future__ import annotations

import re

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "properati"


def parse_detail(html: str, url: str) -> RawListing | None:
    title_m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    title = title_m.group(1) if title_m else ""
    desc_m = re.search(r'name="description"\s+content="([^"]*)"', html)
    description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    price = None
    for pm in re.finditer(r"USD\s*([\d.]+)", html):
        price = parse_price(pm.group(1))
        if price and price > 1000:
            break

    lat = lng = None
    lm = re.search(r'latitude:\s*"(-?[\d.]+)"', html)
    if lm:
        lat = float(lm.group(1))
    lm = re.search(r'longitude:\s*"(-?[\d.]+)"', html)
    if lm:
        lng = float(lm.group(1))

    locality = ""
    loc_m = re.search(r'locality:\s*"([^"]+)"', html)
    if loc_m:
        locality = loc_m.group(1)
    province = ""
    pm = re.search(r'province:\s*"([^"]+)"', html)
    if pm:
        province = pm.group(1)

    images = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images = [om.group(1)]

    external = None
    em = re.search(r'id:\s*"([0-9a-f\-]{20,})"', html)
    if em:
        external = em.group(1)

    bedrooms = first_int(*(m.group(1) for m in re.finditer(r'data-test="bedrooms-value"[^>]*>.*?<span>(\d+)', html, re.S)))

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title[:180] or "Propiedad Properati",
        description=description,
        price=price,
        currency="USD",
        zone=locality,
        city=locality or "La Plata",
        province=province or "Buenos Aires",
        bedrooms=bedrooms,
        rooms=bedrooms,
        property_type="Departamento",
        operation="Venta",
        images=images,
        lat=lat,
        lng=lng,
    )
