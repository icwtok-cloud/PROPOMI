"""Inmobiliaria Gorlero (inmobiliariagorlero.com) — mismo patrón Canepa: /{Tipo}/{id}."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_gorlero_uy"
BASE = "https://www.inmobiliariagorlero.com"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(
        r'href="(https://www\.inmobiliariagorlero\.com/(?:Casa|Apartamento|Terreno|Campo|Local|Oficina)/\d+)"',
        html,
        re.I,
    )
    hrefs += re.findall(
        r'href="(/(?:Casa|Apartamento|Terreno|Campo|Local|Oficina)/\d+)"',
        html,
        re.I,
    )
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url or BASE, h)
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_url(url: str, blob: str) -> str:
    low = url.lower()
    if "/terreno" in low:
        return "Terreno"
    if "/campo" in low or "chacra" in blob or "cabaña" in blob or "cabana" in blob:
        return "Campo" if "/campo" in low else "Casa"
    if "/local" in low or "/oficina" in low:
        return "Local"
    if "/casa" in low:
        return "Casa"
    return "Departamento"


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(r"/(?:Casa|Apartamento|Terreno|Campo|Local|Oficina)/(\d+)", url, re.I)
    external_id = idm.group(1) if idm else None

    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og:
        title = og.group(1).strip()
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).split("-")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    # U$S 34,320
    m = re.search(r"U\$S\s*([\d,]+(?:\.\d+)?)", html[:35000])
    if m:
        try:
            price = float(m.group(1).replace(",", ""))
        except ValueError:
            price = parse_price(m.group(1))
    if price is None:
        m = re.search(r"USD\s*([\d,]+(?:\.\d+)?)", html[:35000], re.I)
        if m:
            try:
                price = float(m.group(1).replace(",", ""))
            except ValueError:
                price = parse_price(m.group(1))

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images.append(om.group(1))
    for m in re.finditer(
        r'src="(https://[^"]+gorlero[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images and "logo" not in m.group(1).lower():
            images.append(m.group(1))
        if len(images) >= 6:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Punta del Este"
    for c in (
        "punta del diablo", "la barra", "jose ignacio", "josé ignacio",
        "maldonado", "montevideo", "rocha", "piriapolis",
    ):
        if c in blob:
            city = c.title().replace("José", "José")
            break

    operation = "Venta"
    if re.search(r"\balquil", title, re.I) and not re.search(r"\bvend", title, re.I):
        operation = "Alquiler"
    else:
        operation = detect_operation_from_signals(url=url, title=title, html=html) or "Venta"

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        city=city,
        province="Maldonado" if "montevideo" not in city.lower() else "Montevideo",
        rooms=first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*dorm", blob, re.I))),
        property_type=_type_from_url(url, blob),
        operation=operation,
        images=images[:5],
        agency_name="Gorlero",
        extras={"country": "Uruguay"},
    )
