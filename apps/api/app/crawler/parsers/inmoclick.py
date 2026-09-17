"""InmoClick — og tags + HTML estructurado (sin SPA challenge)."""
from __future__ import annotations

import re

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "inmoclick"


def parse_detail(html: str, url: str) -> RawListing | None:
    title_m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    title = (title_m.group(1).strip() if title_m else "")[:180]

    desc_m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    description = strip_contact_leaks(desc_m.group(1) if desc_m else "")

    img_m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    images = [img_m.group(1)] if img_m else []

    # Precio: USD / U$S / $ en bloques cercanos a PRECIO
    price = None
    currency = "USD"
    for pat in [
        r"(?:U\$S|US\$|USD)\s*([\d.\s]+)",
        r"\$\s*([\d.\s]{4,})",
    ]:
        pm = re.search(pat, html)
        if pm:
            price = parse_price(pm.group(1))
            if price and price >= 1000:
                if "$" in pat and "USD" not in pat and "U$" not in pat:
                    # heurística: valores > 1e6 suelen ser ARS
                    if price > 500000:
                        currency = "ARS"
                break

    bedrooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d+)\s*(?:dormitorios?|dorm\.?)", html, re.I))
    )
    bathrooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d+)\s*(?:baños?|banos?)", html, re.I))
    )
    surface = None
    sm = re.search(r"(\d+[.,]?\d*)\s*m[²2]\s*(?:tot|de superficie|cub)", html, re.I)
    if sm:
        surface = parse_price(sm.group(1))

    # external id from URL /inmuebles/ID/ficha/
    external = None
    em = re.search(r"/inmuebles/(\d+)/ficha/", url)
    if em:
        external = em.group(1)
    else:
        em = re.search(r"ID#(\d+)", title)
        if em:
            external = em.group(1)

    # provincia heurística
    province = "Buenos Aires"
    low = (title + " " + description + " " + url).lower()
    if "mendoza" in low or "godoy cruz" in low or "guaymall" in low:
        province = "Mendoza"
    elif "cordoba" in low or "córdoba" in low:
        province = "Córdoba"
    elif "santa fe" in low or "rosario" in low:
        province = "Santa Fe"

    zone = ""
    zm = re.search(r"(?:barrio|zona)\s+([A-ZÁÉÍÓÚ][\w\s]{2,40})", description, re.I)
    if zm:
        zone = zm.group(1).strip()[:80]

    if not title:
        return None

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title,
        description=description,
        price=price,
        currency=currency,
        zone=zone,
        city=province,
        province=province,
        surface=surface,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        rooms=bedrooms,
        property_type="Casa" if re.search(r"casa|duplex|dúplex", title, re.I) else "Departamento",
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=images[:5],
    )
