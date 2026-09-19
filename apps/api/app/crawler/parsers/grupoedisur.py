"""Grupo Edisur / Edisur (Córdoba) — desarrollos y pozo."""
from __future__ import annotations

import re

from ..base import RawListing, detect_operation_from_signals, parse_price, strip_contact_leaks

SOURCE = "grupoedisur"


def parse_detail(html: str, url: str) -> RawListing | None:
    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.I)
    if og:
        title = og.group(1).strip()
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        if tm:
            title = re.sub(r"\s*[|\—\-].*$", "", tm.group(1)).strip()
    if not title:
        return None
    title = title[:180]

    description = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html, re.I)
    if dm:
        description = strip_contact_leaks(dm.group(1))
    if not description:
        # WordPress often has entry-content
        em = re.search(
            r'class="[^"]*(?:entry-content|project-description|desarrollo)[^"]*"[^>]*>(.*?)</div>',
            html,
            re.S | re.I,
        )
        if em:
            text = re.sub(r"<[^>]+>", " ", em.group(1))
            description = strip_contact_leaks(re.sub(r"\s+", " ", text).strip()[:2000])

    images: list[str] = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html, re.I)
    if om:
        images.append(om.group(1))
    for m in re.finditer(
        r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        html,
        re.I,
    ):
        u = m.group(1)
        if "logo" in u.lower() or "icon" in u.lower() or "avatar" in u.lower():
            continue
        if u not in images:
            images.append(u)
        if len(images) >= 5:
            break

    price = None
    currency = "USD"
    pm = re.search(
        r"(?:desde\s+)?(?:USD|US\$|U\$S|u\$s)\s*([\d.]+)",
        html,
        re.I,
    )
    if pm:
        price = parse_price(pm.group(1))
    else:
        pm = re.search(r"\$\s*([\d.]+)", html)
        if pm:
            price = parse_price(pm.group(1))
            currency = "ARS"

    zone = "Córdoba"
    city = "Córdoba"
    # Infer zone from URL slug if present
    slug_m = re.search(r"/desarrollos/([^/]+)/", url)
    if slug_m:
        zone = slug_m.group(1).replace("-", " ").title()[:100]

    op = detect_operation_from_signals(url, title, description) or "Venta"
    ptype = "En Pozo"
    blob = f"{url} {title}".lower()
    if "lote" in blob or "terreno" in blob:
        ptype = "Terreno"
    elif "local" in blob or "comercial" in blob:
        ptype = "Local"
    elif "casa" in blob or "casona" in blob or "housing" in blob:
        ptype = "Casa"
    elif "country" in blob:
        ptype = "Casa"

    return RawListing(
        source=SOURCE,
        source_url=url,
        title=title,
        price=price,
        currency=currency,
        operation=op,
        property_type=ptype,
        zone=zone,
        city=city,
        province="Córdoba",
        description=description,
        images=images,
        extras={"country": "Argentina", "under_construction": True},
    )
