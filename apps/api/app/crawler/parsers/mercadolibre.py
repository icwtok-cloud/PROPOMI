"""Mercado Libre Inmuebles — melidata event_data + meta og."""
from __future__ import annotations

import json
import re

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "mercadolibre"


def parse_detail(html: str, url: str) -> RawListing | None:
    # melidata event_data JSON
    price = None
    city = zone = ""
    item_id = None
    currency = "USD"

    mm = re.search(r'melidata\("add","event_data",(\{.*?\})\)\s*;', html, re.S)
    if mm:
        try:
            # puede tener trailing
            raw = mm.group(1)
            # balance braces roughly
            data = json.loads(raw)
            price = parse_price(data.get("price"))
            currency = data.get("currency_id") or "USD"
            city = data.get("city") or ""
            zone = data.get("neighborhood") or ""
            item_id = data.get("item_id")
        except json.JSONDecodeError:
            pass

    if not item_id:
        im = re.search(r"MLA-?(\d+)", url)
        if im:
            item_id = f"MLA{im.group(1)}"

    title_m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    title = title_m.group(1) if title_m else ""
    # strip " - US$ ..."
    title = re.sub(r"\s*-\s*US\$\s*[\d.]+.*$", "", title).strip()

    desc_m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    if price is None:
        pm = re.search(r"US\$\s*([\d.]+)", title_m.group(1) if title_m else "")
        if pm:
            price = parse_price(pm.group(1))

    images = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images = [om.group(1)]

    # ambiente heurística del título
    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*ambientes?", title + " " + description, re.I)))

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=item_id,
        title=title[:180],
        description=description,
        price=price,
        currency=currency,
        zone=zone or city,
        city=city or "Buenos Aires",
        province="Buenos Aires",
        rooms=rooms,
        property_type="Departamento",
        operation="Venta",
        images=images,
        extras={"seller_type": "real_estate"} if "real_estate" in html else {},
    )
