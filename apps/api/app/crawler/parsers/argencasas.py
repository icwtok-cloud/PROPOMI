"""Argencasas (argencasas.com) — RealEstateListing JSON-LD + og fallback."""
from __future__ import annotations

import json
import re

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "argencasas"


def _type_from_url_title(url: str, title: str) -> str:
    blob = f"{url} {title}".lower()
    if "terreno" in blob or "lote" in blob:
        return "Terreno"
    if "campo" in blob or "chacra" in blob or "quinta" in blob:
        return "Campo"
    if re.search(r"\bph\b|duplex|tríplex|triplex", blob):
        return "PH"
    if "local" in blob or "comercial" in blob:
        return "Local"
    if "oficina" in blob:
        return "Oficina"
    if "casa" in blob or "chalet" in blob:
        return "Casa"
    return "Departamento"


def parse_detail(html: str, url: str) -> RawListing | None:
    title = ""
    price = None
    currency = "USD"
    description = ""
    images: list[str] = []
    origin = ""
    external_id = None

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
        if data.get("@type") == "RealEstateListing":
            title = (data.get("name") or title)[:180]
            origin = str(data.get("datePosted") or data.get("datePublished") or origin or "").strip()
            desc = data.get("description")
            if desc:
                description = strip_contact_leaks(str(desc))
            img = data.get("image")
            if isinstance(img, str):
                images = [img]
            elif isinstance(img, list):
                images = [x for x in img if isinstance(x, str)][:5]
            offers = data.get("offers") or {}
            if isinstance(offers, dict):
                price = parse_price(offers.get("price")) or price
                currency = offers.get("priceCurrency") or currency

    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1).strip() if og else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).strip() if tm else ""
    if not title:
        return None

    if price is None:
        pm = re.search(r"(?:U\$S|USD|US\$)\s*([\d.]+)", html, re.I)
        if pm:
            price = parse_price(pm.group(1))
        else:
            pm = re.search(r"\$\s*([\d.]+)", html)
            if pm:
                price = parse_price(pm.group(1))
                currency = "ARS"

    if not description:
        dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(dm.group(1) if dm else "")

    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    # external id from trailing -{n}-{m} or last numeric group
    idm = re.search(r"(\d{2,})-(\d{2,})$", url.rstrip("/"))
    if idm:
        external_id = f"{idm.group(1)}-{idm.group(2)}"
    else:
        idm = re.search(r"(\d{4,})", url)
        external_id = idm.group(1) if idm else None

    # Location heuristics from title / breadcrumb
    zone = city = ""
    # "Casa en Venta en Quilmes Oeste"
    loc = re.search(r"en\s+Venta\s+en\s+(.+)$", title, re.I)
    if loc:
        city = loc.group(1).strip()[:80]
        zone = city

    rooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d)\s*amb", title + " " + description, re.I))
    )
    ptype = _type_from_url_title(url, title)

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
        province="Buenos Aires",
        rooms=rooms,
        property_type=ptype,
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=images[:5],
        origin_published_at=origin or None,
    )
