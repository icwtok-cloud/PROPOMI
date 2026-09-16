"""InfoCasas (infocasas.com.py / .uy) — ficha con __NEXT_DATA__.pageProps.data."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, first_int, parse_price, strip_contact_leaks


def extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_detail(html: str, url: str, source: str, default_country: str) -> RawListing | None:
    root = extract_next_data(html)
    if not root:
        return None
    data = ((root.get("props") or {}).get("pageProps") or {}).get("data") or {}
    if not data or not data.get("title"):
        return None

    price_obj = data.get("price") or {}
    amount = price_obj.get("amount") if isinstance(price_obj, dict) else None
    cur = "USD"
    if isinstance(price_obj, dict):
        c = (price_obj.get("currency") or {}).get("name") or ""
        if "U$" in c or "USD" in c.upper():
            cur = "USD"
        elif "GS" in c.upper() or "PYG" in c.upper():
            cur = "PYG"
        elif "$U" in c or "UYU" in c.upper():
            cur = "UYU"
        elif "ARS" in c.upper() or c.strip() == "$":
            cur = "ARS"

    locs = data.get("locations") or {}
    zone = (
        (locs.get("neighbourhood") or locs.get("zone") or locs.get("locality") or {}).get("name")
        if isinstance(locs.get("neighbourhood") or locs.get("zone") or locs.get("locality"), dict)
        else ""
    )
    if not zone and isinstance(locs.get("neighbourhood"), str):
        zone = locs["neighbourhood"]
    # fallback from address "San Jorge, Asunción, Paraguay"
    addr = data.get("address") or ""
    if not zone and addr:
        zone = addr.split(",")[0].strip()
    city = ""
    if isinstance(locs.get("city"), dict):
        city = locs["city"].get("name") or ""
    if not city and addr:
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        city = parts[1] if len(parts) > 1 else parts[0]

    ptype = "Departamento"
    pt = data.get("property_type") or {}
    if isinstance(pt, dict) and pt.get("name"):
        ptype = pt["name"]

    op = "Venta"
    ot = data.get("operation_type") or {}
    if isinstance(ot, dict) and ot.get("name"):
        op = ot["name"]

    images: list[str] = []
    for im in data.get("images") or []:
        if isinstance(im, dict) and im.get("image"):
            images.append(im["image"])
        elif isinstance(im, str):
            images.append(im)
    if not images and data.get("img"):
        images = [data["img"]]

    seller = data.get("seller") or data.get("owner") or {}
    agency_name = ""
    if isinstance(seller, dict):
        agency_name = seller.get("name") or ""

    return RawListing(
        source=source,
        source_url=url,
        external_id=str(data.get("id") or data.get("code") or ""),
        title=(data.get("title") or "")[:200],
        description=strip_contact_leaks(data.get("description")),
        price=parse_price(amount),
        currency=cur,
        zone=zone or "",
        city=city or default_country,
        province=city or default_country,
        address=addr,
        surface=parse_price(data.get("m2") or data.get("m2Built")),
        surface_covered=parse_price(data.get("m2Built") or data.get("m2apto")),
        bedrooms=first_int(data.get("bedrooms")),
        bathrooms=first_int(data.get("bathrooms")),
        rooms=first_int(data.get("rooms"), data.get("bedrooms")),
        property_type=ptype,
        operation=op,
        images=images[:5],
        lat=float(data["latitude"]) if data.get("latitude") else None,
        lng=float(data["longitude"]) if data.get("longitude") else None,
        agency_name=agency_name,
        extras={"country": default_country, "code": data.get("code")},
    )


def parse_detail_py(html: str, url: str) -> RawListing | None:
    return _parse_detail(html, url, "infocasas_py", "Paraguay")


def parse_detail_uy(html: str, url: str) -> RawListing | None:
    return _parse_detail(html, url, "infocasas_uy", "Uruguay")
