"""BienesOnline (bienesonline.ai) — JSON-LD RealEstateListing + Place + Offer."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "bienesonline"


def _ld_graph(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "@graph" in data:
            out.extend([x for x in data["@graph"] if isinstance(x, dict)])
        elif isinstance(data, dict):
            out.append(data)
        elif isinstance(data, list):
            out.extend([x for x in data if isinstance(x, dict)])
    return out


def parse_detail(html: str, url: str) -> RawListing | None:
    graph = _ld_graph(html)
    listing = next((g for g in graph if g.get("@type") == "RealEstateListing"), None)
    place = next((g for g in graph if g.get("@type") in ("Place", "Accommodation", "House", "Apartment")), None)
    offer = next((g for g in graph if g.get("@type") == "Offer"), None)
    if not listing and not place:
        return None

    title = (listing or {}).get("name") or (place or {}).get("name") or ""
    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1) if og else ""
    if not title:
        return None

    desc = strip_contact_leaks((listing or {}).get("description") or "")
    images = (listing or {}).get("image") or []
    if isinstance(images, str):
        images = [images]

    price = None
    currency = "USD"
    if offer:
        price = parse_price(offer.get("price"))
        currency = offer.get("priceCurrency") or "USD"

    addr = (place or {}).get("address") or {}
    zone = ""
    city = ""
    province = ""
    if isinstance(addr, dict):
        city = addr.get("addressLocality") or ""
        province = addr.get("addressRegion") or ""
        zone = city
    elif isinstance(addr, str):
        zone = addr

    bedrooms = first_int((place or {}).get("numberOfBedrooms"))
    bathrooms = first_int((place or {}).get("numberOfBathroomsTotal"))
    surface = None
    fs = (place or {}).get("floorSize") or (place or {}).get("lotSize") or {}
    if isinstance(fs, dict):
        surface = parse_price(fs.get("value"))

    external = None
    em = re.search(r"/propiedad/(\d+)", url)
    if em:
        external = em.group(1)

    seller = (offer or {}).get("seller") or {}
    agency = ""
    if isinstance(seller, dict):
        agency = (seller.get("worksFor") or {}).get("name") if isinstance(seller.get("worksFor"), dict) else seller.get("name") or ""

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title[:200],
        description=desc,
        price=price,
        currency=currency,
        zone=zone,
        city=city or zone,
        province=province or "Argentina",
        surface=surface,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        rooms=bedrooms,
        property_type="Terreno" if (surface and bedrooms == 0) else "Propiedad",
        operation="Venta",
        images=list(images)[:5],
        agency_name=agency or "",
        extras={"country": "AR"},
    )
