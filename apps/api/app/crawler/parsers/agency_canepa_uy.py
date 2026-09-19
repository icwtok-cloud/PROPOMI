"""Cánepa & Cánepa (canepa.com.uy) — listados /casas|apartamentos|terrenos/en-venta/ + ficha /{Tipo}/{id}."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_canepa_uy"
BASE = "https://www.canepa.com.uy"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(
        r'href="(https://www\.canepa\.com\.uy/(?:Casa|Apartamento|Terreno|Campo|Local|Oficina)/\d+)"',
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
    if "/terreno" in low or "terreno" in blob:
        return "Terreno"
    if "/campo" in low or "campo" in blob or "chacra" in blob:
        return "Campo"
    if "/local" in low or "/oficina" in low:
        return "Local"
    if "/casa" in low or "casa" in blob:
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
        h1 = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
        title = h1.group(1).strip() if h1 else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).split("-")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    # USD 890,000 — coma = miles
    price = None
    currency = "USD"
    m = re.search(r"USD\s*([\d,]+(?:\.\d+)?)", html[:30000], re.I)
    if m:
        raw = m.group(1).replace(",", "")
        try:
            price = float(raw)
        except ValueError:
            price = parse_price(raw)
    if price is None:
        m = re.search(r"U\$S\s*([\d.]+)", html[:30000])
        if m:
            price = parse_price(m.group(1))

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))
    if not desc:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        if dm:
            desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images.append(om.group(1))
    for m in re.finditer(
        r'src="(https://[^"]+canepa[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images and "logo" not in m.group(1).lower():
            images.append(m.group(1))
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Punta del Este"
    for c in (
        "montevideo", "maldonado", "la barra", "jose ignacio", "josé ignacio",
        "rocha", "colonia", "piriapolis", "piriápolis",
    ):
        if c in blob:
            city = c.replace("josé", "Jose").title().replace("Jose Ignacio", "José Ignacio")
            break

    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*dorm", blob, re.I)))
    operation = detect_operation_from_signals(url=url, title=title, html=html) or "Venta"
    if "alquiler" in blob and "venta" not in blob:
        operation = "Alquiler"

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        city=city,
        province="Maldonado" if city != "Montevideo" else "Montevideo",
        rooms=rooms,
        bedrooms=rooms,
        property_type=_type_from_url(url, blob),
        operation=operation,
        images=images[:5],
        agency_name="Cánepa & Cánepa",
        extras={"country": "Uruguay"},
    )
