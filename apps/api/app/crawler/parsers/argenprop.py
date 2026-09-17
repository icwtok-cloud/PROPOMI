"""Argenprop — meta + form card + ld+json Organization/WebSite (ficha usa HTML semántico)."""
from __future__ import annotations

import html as html_lib
import re

from ..base import RawListing, first_int, parse_price, strip_contact_leaks

SOURCE = "argenprop"


def parse_detail(html: str, url: str) -> RawListing | None:
    title_m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    title = html_lib.unescape(title_m.group(1) if title_m else "")
    if not title:
        tm = re.search(r"<title>([^|<]+)", html)
        title = html_lib.unescape(tm.group(1).strip() if tm else "")

    desc_m = re.search(r'name="description"\s+content="([^"]*)"', html)
    description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    price = None
    pm = re.search(r'class="fix-main__price"[^>]*>\s*USD\s*([\d.]+)', html)
    if pm:
        price = parse_price(pm.group(1))
    if price is None:
        pm = re.search(r'property-price-currency[^>]*>\s*USD\s*</span>\s*([\d.]+)', html)
        if pm:
            price = parse_price(pm.group(1))

    address = ""
    am = re.search(r'class="fix-main__address"[^>]*>([^<]+)', html)
    if am:
        address = am.group(1).strip()

    loc = ""
    lm = re.search(r'class="fix-location"[^>]*>([^<]+)', html)
    if lm:
        loc = lm.group(1).strip()
    # "Departamento en Venta en Olivos, Partido de Vicente López"
    zone = "Olivos"
    if "en " in loc:
        zone = loc.split("en ")[-1].split(",")[0].strip()

    surface = None
    sm = re.search(r"([\d.]+)\s*m²\s*Cubierta", html)
    if sm:
        surface = parse_price(sm.group(1))

    bedrooms = first_int(*(x.group(1) for x in re.finditer(r"(\d+)\s*dormitorio", html, re.I)))
    # antigüedad etc. no crítica

    images = []
    om = re.search(r'property="og:image"[^>]*content="([^"]+)"|content="([^"]+)"[^>]*property="og:image"', html)
    if om:
        images = [om.group(1) or om.group(2)]

    external = None
    em = re.search(r"--(\d+)\s*$", url.rstrip("/")) or re.search(r"idAviso=(\d+)", html)
    if em:
        external = em.group(1)

    origin = ""
    for pat in (
        r'property="article:published_time"\s+content="([^"]+)"',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateModified"\s*:\s*"([^"]+)"',
        r"Publicado\s+(?:el\s+)?(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
    ):
        m = re.search(pat, html, re.I)
        if m:
            origin = m.group(1).strip()
            break

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title[:180],
        description=description,
        price=price,
        currency="USD",
        zone=zone,
        city="Buenos Aires",
        province="Buenos Aires",
        address=address,
        surface=surface,
        bedrooms=bedrooms,
        rooms=bedrooms,
        property_type="Departamento",
        operation="Venta",
        images=images,
        origin_published_at=origin or None,
    )
