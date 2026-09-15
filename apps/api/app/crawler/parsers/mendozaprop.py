"""MendozaProp — ficha con __NEXT_DATA__ (Next.js)."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "mendozaprop"


def extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def parse_detail(html: str, url: str) -> RawListing | None:
    root = extract_next_data(html)
    if not root:
        return None
    data = (root.get("props") or {}).get("pageProps", {}).get("data") or {}
    if not data:
        return None
    images = data.get("images") or []
    addr = data.get("address") or ""
    # "El Limon, Mendoza, Argentina"
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    zone = parts[0] if parts else ""
    city = parts[1] if len(parts) > 1 else "Mendoza"
    currency_id = data.get("currency_id")
    currency = "USD" if currency_id in (1, "1", None) else "ARS"
    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=str(data.get("id") or ""),
        title=data.get("title") or "",
        description=strip_contact_leaks(data.get("description")),
        price=parse_price(data.get("price")),
        currency=currency,
        zone=zone,
        city=city,
        province="Mendoza",
        address=addr,
        surface=parse_price(data.get("m2")),
        surface_covered=parse_price(data.get("m2_covered")),
        bedrooms=first_int(data.get("bedrooms")),
        bathrooms=first_int(data.get("bathrooms")),
        rooms=first_int(data.get("rooms"), data.get("bedrooms")),
        parking=bool(data.get("parking")),
        credit=bool(data.get("credit")),
        property_type="Casa" if data.get("property_type_id") == 3 else "Departamento",
        operation="Venta" if data.get("transaction_type_id") == 2 else "Venta",
        images=list(images)[:5],
        lat=float(data["google_lat"]) if data.get("google_lat") else None,
        lng=float(data["google_lng"]) if data.get("google_lng") else None,
        extras={"owner_id": data.get("owner_id"), "amenities": data.get("amenities")},
    )
