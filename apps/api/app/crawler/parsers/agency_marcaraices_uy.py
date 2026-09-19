"""Marca Raíces (marcaraices.com) — mismo patrón Canepa/Gorlero: /{Tipo}/{id} + listados en-venta."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_marcaraices_uy"
BASE = "https://www.marcaraices.com"

_TYPE_RE = r"(?:Apartamento|Casa|Terreno|Campo|Chacra|Local|Oficina|Galpon)"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(
        rf'href="(https://www\.marcaraices\.com/{_TYPE_RE}/\d+)"',
        html,
        re.I,
    )
    hrefs += re.findall(rf'href="(/{_TYPE_RE}/\d+)"', html, re.I)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url or BASE, h)
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_url(url: str, blob: str) -> str:
    # Priorizar path de la URL (el blob puede decir "Casa X" como nombre de emprendimiento)
    low = url.lower()
    if "/terreno/" in low:
        return "Terreno"
    if "/campo/" in low or "/chacra/" in low:
        return "Campo"
    if "/local/" in low or "/oficina/" in low or "/galpon/" in low:
        return "Local"
    if "/casa/" in low:
        return "Casa"
    if "/apartamento/" in low:
        return "Departamento"
    if "terreno" in blob:
        return "Terreno"
    if "campo" in blob or "chacra" in blob:
        return "Campo"
    if "casa" in blob:
        return "Casa"
    return "Departamento"


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(rf"/{_TYPE_RE}/(\d+)", url, re.I)
    external_id = idm.group(1) if idm else None

    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og:
        title = og.group(1).strip()
        # Quitar sufijo " - Marca Raices..."
        title = re.split(r"\s+-\s+Marca", title, maxsplit=1)[0].strip()
    if not title:
        h1 = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
        title = h1.group(1).strip() if h1 else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).split("-")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    # USD 103.700 (punto = miles) o USD103.700; ignorar montos < 1000 (ruido de UI)
    chunk = html[:60000].replace("\xa0", " ").replace("\u00a0", " ")
    m = re.search(r"USD\s*([\d.]+(?:\s[\d]{3})*)", chunk, re.I)
    if m:
        raw = re.sub(r"[.\s]", "", m.group(1))
        try:
            cand = float(raw)
            if cand >= 1000:
                price = cand
        except ValueError:
            price = parse_price(m.group(1))
    if price is None:
        m = re.search(r"U\$S\s*([\d.]+)", chunk[:40000])
        if m:
            cand = parse_price(m.group(1).replace(".", ""))
            if cand and cand >= 1000:
                price = cand

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
        r'src="(https://[^"]+marcaraices[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images and "logo" not in m.group(1).lower():
            images.append(m.group(1))
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Montevideo"
    for c in (
        "montevideo", "pocitos", "punta carretas", "carrasco", "malvin",
        "tres cruces", "cordon", "cordón", "punta del este", "maldonado",
        "la barra", "colonia", "canelones", "ciudad de la costa",
    ):
        if c in blob:
            city = c.replace("cordón", "Cordon").title().replace("Cordon", "Cordón")
            break

    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:dorm|amb)", blob, re.I)))
    operation = detect_operation_from_signals(url=url, title=title, html=html) or "Venta"
    if "alquiler" in blob and "venta" not in blob:
        operation = "Alquiler"

    province = "Montevideo"
    if any(x in city.lower() for x in ("punta del este", "maldonado", "la barra")):
        province = "Maldonado"
    elif "colonia" in city.lower():
        province = "Colonia"
    elif "canelones" in city.lower() or "costa" in city.lower():
        province = "Canelones"

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        city=city,
        province=province,
        rooms=rooms,
        bedrooms=rooms,
        property_type=_type_from_url(url, blob),
        operation=operation,
        images=images[:5],
        agency_name="Marca Raíces",
        extras={"country": "Uruguay"},
    )
