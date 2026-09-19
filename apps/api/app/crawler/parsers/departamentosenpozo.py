"""departamentosenpozo.com.ar — catálogo de desarrollos en pozo (CABA/GBA)."""
from __future__ import annotations

import json
import re

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "departamentosenpozo"


def parse_detail(html: str, url: str) -> RawListing | None:
    title = ""
    price = None
    currency = "USD"
    description = ""
    images: list[str] = []
    origin = ""
    zone = city = "CABA"
    province = "CABA"

    # JSON-LD
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type")
            if t in ("Product", "Apartment", "Residence", "RealEstateListing", "Offer"):
                title = (obj.get("name") or title)[:180]
                if obj.get("description"):
                    description = strip_contact_leaks(str(obj.get("description")))
                offers = obj.get("offers") if t != "Offer" else obj
                if isinstance(offers, dict):
                    price = parse_price(offers.get("price") or offers.get("lowPrice")) or price
                    currency = offers.get("priceCurrency") or currency
                img = obj.get("image")
                if isinstance(img, str):
                    images = [img]
                elif isinstance(img, list) and img:
                    images = [x if isinstance(x, str) else x.get("url", "") for x in img if x][:5]
                addr = obj.get("address")
                if isinstance(addr, dict):
                    city = addr.get("addressLocality") or city
                    zone = addr.get("addressLocality") or zone
                    province = addr.get("addressRegion") or province

    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1).strip() if og else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = re.sub(r"\s*[|\—\-].*$", "", tm.group(1)).strip() if tm else ""
    if not title:
        return None

    # "Desde USD 110.000" patterns common on this site
    if price is None:
        pm = re.search(
            r"(?:desde\s+)?(?:USD|US\$|U\$S)\s*([\d.]+)",
            html,
            re.I,
        )
        if pm:
            price = parse_price(pm.group(1))

    if not description:
        dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(dm.group(1) if dm else "")

    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    # slug as external id
    slug_m = re.search(r"/desarrollos-inmobiliarios/([^/]+)/?", url)
    external_id = slug_m.group(1) if slug_m else None

    # barrio often in title after em-dash or colon
    for pat in (r"[—\-:]\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)$", r"en\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)$"):
        bm = re.search(pat, title)
        if bm:
            zone = bm.group(1).strip()[:80]
            city = zone
            break

    rooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d)\s*amb", title + " " + description, re.I))
    )

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title[:180],
        description=description,
        price=price,
        currency=currency,
        zone=zone,
        city=city,
        province=province if province != "CABA" else "CABA",
        rooms=rooms,
        property_type="En Pozo",
        operation=detect_operation_from_signals(url=url, html=html, title=title) or "Venta",
        images=images[:5],
        origin_published_at=origin or None,
        extras={"under_construction": True},
    )
