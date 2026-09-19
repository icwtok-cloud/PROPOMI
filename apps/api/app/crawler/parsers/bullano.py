"""Bullano — campos y chacras (bullano.com.ar/campos/ficha/...)."""
from __future__ import annotations

import json
import re

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "bullano"


def parse_detail(html: str, url: str) -> RawListing | None:
    title = ""
    price = None
    currency = "USD"
    description = ""
    images: list[str] = []
    origin = ""
    zone = city = province = ""
    surface = None

    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") in ("Product", "RealEstateListing", "Offer", "Place"):
            title = (data.get("name") or title)[:180]
            if data.get("description"):
                description = strip_contact_leaks(str(data.get("description")))
            offers = data.get("offers") or (data if data.get("@type") == "Offer" else {})
            if isinstance(offers, dict):
                price = parse_price(offers.get("price")) or price
                currency = offers.get("priceCurrency") or currency
            img = data.get("image")
            if isinstance(img, str):
                images = [img]
            elif isinstance(img, list) and img:
                images = [x if isinstance(x, str) else "" for x in img][:5]

    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1).strip() if og else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).strip() if tm else ""
    if not title:
        return None

    if price is None:
        pm = re.search(r"(?:u\$s|USD|US\$)\s*([\d.]+)", html, re.I)
        if pm:
            price = parse_price(pm.group(1))

    if not description:
        dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(dm.group(1) if dm else "")

    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    # "Campo en Venta en San Rafael" / province hints
    loc = re.search(r"en\s+(?:Venta\s+en\s+)?([^,\-|]+)", title, re.I)
    if loc:
        city = loc.group(1).strip()[:80]
        zone = city
    for prov in (
        "Buenos Aires", "Córdoba", "Mendoza", "Santa Fe", "Salta", "Misiones",
        "Chubut", "Río Negro", "Neuquén", "La Pampa", "San Luis", "Entre Ríos",
        "Corrientes", "Tucumán", "Catamarca", "Santiago del Estero",
    ):
        if prov.lower() in (title + " " + description).lower():
            province = prov
            break
    if not province:
        province = "Buenos Aires"

    # hectares
    hm = re.search(r"([\d.,]+)\s*ha(?:s|ctáreas|ctareas)?", title + " " + description, re.I)
    if hm:
        try:
            surface = float(hm.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            surface = None

    idm = re.search(r"-(\d+)\.html", url)
    external_id = idm.group(1) if idm else None

    ptype = "Chacra" if "chacra" in (title + url).lower() else "Campo"

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title[:180],
        description=description,
        price=price,
        currency=currency,
        zone=zone,
        city=city or zone,
        province=province,
        rooms=None,
        surface=surface,
        property_type=ptype,
        operation=detect_operation_from_signals(url=url, html=html, title=title) or "Venta",
        images=images[:5],
        origin_published_at=origin or None,
    )
