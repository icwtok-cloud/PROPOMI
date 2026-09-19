"""Orange Home (Guadalajara) — listado home + fichas /{id}/inmuebles/{slug}."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_orangehome_mx"
BASE = "https://www.orangehomeinmobiliaria.com.mx"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(
        r'href="(https://www\.orangehomeinmobiliaria\.com\.mx/\d+/inmuebles/[^"]+)"',
        html,
    )
    hrefs += re.findall(r'href="(/\d+/inmuebles/[^"]+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url or BASE, h)
        low = full.lower()
        # Priorizar venta; descartar renta pura
        if "renta" in low and "venta" not in low:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_blob(blob: str) -> str:
    b = blob.lower()
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "local" in b or "comercial" in b:
        return "Local"
    if "oficina" in b:
        return "Oficina"
    if "departamento" in b or "depto" in b or "apto" in b:
        return "Departamento"
    if "casa" in b or "dúplex" in b or "duplex" in b:
        return "Casa"
    return "Casa"


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(r"/(\d+)/inmuebles/", url)
    external_id = idm.group(1) if idm else None

    title = ""
    h1 = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
    if h1:
        title = h1.group(1).strip()
    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1).strip() if og else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "MXN"

    def _mx_price(raw: str) -> float | None:
        # MX: 1,850,000.00 → quitar comas de miles; punto = decimal
        s = raw.strip().replace(",", "").replace(" ", "")
        try:
            return float(s) if s else None
        except ValueError:
            return None

    amounts: list[float] = []
    for m in re.finditer(r"([\d,]+(?:\.\d+)?)\s*MXN", html[:50000], re.I):
        pval = _mx_price(m.group(1))
        if pval and 30_000 <= pval <= 80_000_000:
            amounts.append(pval)
    for m in re.finditer(r"MXN\s*([\d,]+(?:\.\d+)?)", html[:50000], re.I):
        pval = _mx_price(m.group(1))
        if pval and 30_000 <= pval <= 80_000_000:
            amounts.append(pval)
    if amounts:
        # precio de venta suele ser el mayor en el rango razonable
        price = max(amounts)
    if price is None:
        for mm in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)", html[:40000]):
            pval = _mx_price(mm.group(1))
            if pval and 50_000 <= pval <= 80_000_000:
                amounts.append(pval)
        if amounts:
            price = max(amounts)

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
        r'src="(https://www\.orangehomeinmobiliaria\.com\.mx/admin/imovel/[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images:
            images.append(m.group(1))
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Guadalajara"
    for c in ("zapopan", "tlaquepaque", "tlajomulco", "tonala", "tonalá", "el salto"):
        if c in blob:
            city = c.replace("tonalá", "Tonalá").title()
            break
    zone = ""
    for z in (
        "libertad", "ladron de guevara", "ladrón de guevara", "bosques de santa anita",
        "el tapatío", "el tapatio", "providencia", "chapalita", "americana",
    ):
        if z in blob:
            zone = z.title()
            break

    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*rec[aá]maras?", blob, re.I)))
    bedrooms = rooms
    surface = None
    sm = re.search(r"(\d{2,4})\s*m(?:2|²)", blob, re.I)
    if sm:
        try:
            surface = float(sm.group(1))
        except ValueError:
            pass

    if "/venta-" in url.lower() or " en venta" in title.lower():
        operation = "Venta"
    elif "renta" in blob and "venta" not in blob:
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
        zone=zone,
        city=city,
        province="Jalisco",
        surface=surface,
        rooms=rooms,
        bedrooms=bedrooms,
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name="Orange Home",
        extras={"country": "México"},
    )
