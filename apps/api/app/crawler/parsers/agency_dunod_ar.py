"""Dunod Propiedades (dunod.com.ar) — WP /inmueble/{slug}/ + listado status=venta."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_dunod_ar"
BASE = "https://dunod.com.ar"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(https://dunod\.com\.ar/inmueble/[^"]+/)"', html)
    hrefs += re.findall(r'href="(/inmueble/[^"]+/)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url or BASE, h)
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_blob(blob: str) -> str:
    b = blob.lower()
    if "galpon" in b or "galpón" in b or "deposito" in b:
        return "Local"
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "local" in b or "oficina" in b or "comercial" in b:
        return "Local"
    if "casa" in b or "ph" in b or "duplex" in b:
        return "Casa"
    if "departamento" in b or "depto" in b:
        return "Departamento"
    return "Departamento"


def parse_detail(html: str, url: str) -> RawListing | None:
    # slug as external id
    idm = re.search(r"/inmueble/([^/]+)/?", url)
    external_id = idm.group(1) if idm else None

    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og:
        title = og.group(1).split("-")[0].strip()
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).split("-")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    m = re.search(r'"price"\s*:\s*"?([\d.]+)', html)
    if m:
        price = parse_price(m.group(1))
    if price is None:
        for pat, cur in (
            (r"U\$S\s*([\d.]+)", "USD"),
            (r"USD\s*([\d.]+)", "USD"),
            (r"ARS\s*([\d.]+)", "ARS"),
        ):
            mm = re.search(pat, html[:30000], re.I)
            if mm:
                price = parse_price(mm.group(1))
                currency = cur
                break

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images.append(om.group(1))
    for m in re.finditer(
        r'src="(https://dunod\.com\.ar/wp-content/uploads/[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images:
            images.append(m.group(1))
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Rosario"
    for z in ("funes", "fisherton", "pichincha", "centro", "alberdi", "echeortu", "modern"):
        if z in blob:
            break
    zone = ""
    for z in ("fisherton", "pichincha", "centro", "alberdi", "funes", "republica de la sexta"):
        if z in blob:
            zone = z.title()
            break

    blob_op = f"{url} {title}".lower()
    if re.search(r"\balquil", blob_op) and not re.search(r"\bventa|\bvend", blob_op):
        operation = "Alquiler"
    else:
        operation = "Venta"  # listado status=venta; site chrome dice "Alquiler y venta"

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        zone=zone,
        city=city,
        province="Santa Fe",
        rooms=first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:amb|dorm)", blob, re.I))),
        surface=None,
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name="Dunod",
        extras={"country": "Argentina"},
    )
