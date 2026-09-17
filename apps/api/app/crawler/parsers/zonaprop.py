"""ZonaProp — JSON-LD Apartment + avisoInfo / datos embebidos."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "zonaprop"


def _all_ld_json(html: str) -> list[dict[str, Any]]:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">\s*(\{.*?\}|\[.*?\])\s*</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                out.extend(data)
            else:
                out.append(data)
        except json.JSONDecodeError:
            continue
    return out


def parse_detail(html: str, url: str) -> RawListing | None:
    ld_items = _all_ld_json(html)
    apartment = next((x for x in ld_items if x.get("@type") in ("Apartment", "House", "Product", "RealEstateListing", "SingleFamilyResidence")), None)

    title = ""
    description = ""
    price = None
    currency = "USD"
    rooms = bedrooms = bathrooms = None
    surface = None
    address = zone = city = ""
    phone = ""
    images: list[str] = []

    if apartment:
        title = apartment.get("name") or apartment.get("headline") or ""
        description = strip_contact_leaks(apartment.get("description"))
        rooms = first_int(apartment.get("numberOfRooms"))
        bedrooms = first_int(apartment.get("numberOfBedrooms"))
        bathrooms = first_int(apartment.get("numberOfBathroomsTotal"))
        fs = apartment.get("floorSize") or {}
        if isinstance(fs, dict):
            surface = parse_price(fs.get("value"))
        addr = apartment.get("address") or {}
        if isinstance(addr, dict):
            address = addr.get("streetAddress") or ""
            zone = addr.get("addressRegion") or addr.get("addressLocality") or ""
            city = addr.get("addressLocality") or "Buenos Aires"
        phone = apartment.get("telephone") or ""
        img = apartment.get("image")
        if isinstance(img, list):
            images = img[:5]
        elif isinstance(img, str):
            images = [img]
        offers = apartment.get("offers") or {}
        if isinstance(offers, dict):
            price = parse_price(offers.get("price"))
            currency = offers.get("priceCurrency") or currency

    # Fecha de publicación / modificación en JSON-LD (si el portal la expone)
    origin = ""
    if apartment:
        origin = (
            apartment.get("datePublished")
            or apartment.get("dateModified")
            or apartment.get("dateCreated")
            or ""
        )
        if isinstance(origin, dict):
            origin = origin.get("value") or origin.get("@value") or ""
        origin = str(origin or "").strip()
    if not origin:
        # meta article:published_time u og
        for pat in (
            r'property="article:published_time"\s+content="([^"]+)"',
            r'property="og:updated_time"\s+content="([^"]+)"',
            r'"datePublished"\s*:\s*"([^"]+)"',
            r'"dateModified"\s*:\s*"([^"]+)"',
        ):
            m = re.search(pat, html)
            if m:
                origin = m.group(1).strip()
                break

    # Meta / title fallback
    if not title:
        tm = re.search(r"<title>([^|<]+)", html)
        title = (tm.group(1).strip() if tm else "")[:180]
    if not description:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(dm.group(1) if dm else "")
    if not images:
        om = re.search(r'property="og:image"[^>]+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]
    if price is None:
        # buscar precios en scripts
        for pm in re.finditer(r'"(?:price|amount)"\s*:\s*"?(\d{4,})"?', html):
            price = parse_price(pm.group(1))
            if price and price > 5000:
                break

    # posting id
    external = None
    em = re.search(r"(\d{7,})\.html", url)
    if em:
        external = em.group(1)

    # Palermo / barrio from keywords or title
    if not zone:
        for b in ("Palermo", "Caballito", "Belgrano", "Recoleta", "Botánico"):
            if b.lower() in html.lower():
                zone = b
                break

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title,
        description=description,
        price=price,
        currency=currency,
        zone=zone,
        city=city or "Buenos Aires",
        province="CABA",
        address=address,
        surface=surface,
        rooms=rooms or bedrooms,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        property_type="Departamento",
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=images,
        agency_phone=phone,  # no subir a Property pública; solo hint interno
        origin_published_at=origin or None,
    )
