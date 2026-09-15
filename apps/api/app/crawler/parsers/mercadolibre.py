"""Mercado Libre Inmuebles — JSON-LD Product + melidata + og."""
from __future__ import annotations

import json
import re

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "mercadolibre"


def _province_from_url_or_html(url: str, html: str) -> str:
    u = url.lower()
    h = html.lower()
    for key, name in [
        ("cordoba", "Córdoba"),
        ("c%C3%B3rdoba", "Córdoba"),
        ("mendoza", "Mendoza"),
        ("santa-fe", "Santa Fe"),
        ("santa_fe", "Santa Fe"),
        ("buenos-aires", "Buenos Aires"),
        ("capital-federal", "Buenos Aires"),
        ("caba", "Buenos Aires"),
    ]:
        if key in u or key in h[:5000]:
            return name
    return "Buenos Aires"


def parse_detail(html: str, url: str) -> RawListing | None:
    price = None
    currency = "USD"
    title = ""
    description = ""
    images: list[str] = []
    item_id = None
    city = zone = ""

    # 1) JSON-LD Product (más estable)
    for m in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("@type") == "Product" or "offers" in data:
            title = (data.get("name") or title)[:180]
            offers = data.get("offers") or {}
            if isinstance(offers, dict):
                price = parse_price(offers.get("price")) or price
                currency = offers.get("priceCurrency") or currency
            img = data.get("image")
            if isinstance(img, str):
                images = [img]
            elif isinstance(img, list) and img:
                images = [x for x in img if isinstance(x, str)][:5]
            sku = data.get("sku") or data.get("productID")
            if sku:
                item_id = str(sku)

    # 2) melidata fallback
    if price is None:
        mm = re.search(r'melidata\("add","event_data",(\{.*?\})\)\s*;', html, re.S)
        if mm:
            try:
                data = json.loads(mm.group(1))
                price = parse_price(data.get("price"))
                currency = data.get("currency_id") or currency
                city = data.get("city") or city
                zone = data.get("neighborhood") or zone
                if data.get("item_id"):
                    item_id = data.get("item_id")
            except json.JSONDecodeError:
                pass

    if not item_id:
        im = re.search(r"MLA-?(\d+)", url)
        if im:
            item_id = f"MLA{im.group(1)}"

    if not title:
        title_m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = title_m.group(1) if title_m else ""
        title = re.sub(r"\s*-\s*US\$\s*[\d.]+.*$", "", title).strip()[:180]

    if not description:
        desc_m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    if price is None:
        pm = re.search(r"(?:US\$|USD)\s*([\d.]+)", html)
        if pm:
            price = parse_price(pm.group(1))

    rooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d)\s*ambientes?", title + " " + description, re.I))
    )
    province = _province_from_url_or_html(url, html)

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=item_id,
        title=title[:180],
        description=description,
        price=price,
        currency=currency,
        zone=zone or city,
        city=city or province,
        province=province,
        rooms=rooms,
        property_type="Casa" if "casa" in (title + url).lower() else "Departamento",
        operation="Venta",
        images=images[:5],
    )
