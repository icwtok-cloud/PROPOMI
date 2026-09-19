"""Nueva Alianza (inmobiliariana.com.py) — fichas /propiedad/{id}."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_nuevaalianza_py"
BASE = "https://inmobiliariana.com.py"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(/propiedad/\d+)"', html)
    hrefs += re.findall(r'href="(https://inmobiliariana\.com\.py/propiedad/\d+)"', html)
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
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "casa" in b:
        return "Casa"
    if "departamento" in b or "depto" in b or "apto" in b:
        return "Departamento"
    if "local" in b or "oficina" in b:
        return "Local"
    return "Casa"


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(r"/propiedad/(\d+)", url)
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
    # Sitio a veces deja title genérico; exigir algo usable
    if not title or title.lower().startswith("nueva alianza"):
        # intentar otro heading
        h2 = re.search(r"<h2[^>]*>([^<]+)", html, re.I)
        if h2 and len(h2.group(1).strip()) > 8:
            title = h2.group(1).strip()
    if not title or len(title) < 4:
        title = f"Propiedad {external_id}" if external_id else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]
    if re.search(r"\balquil", title, re.I) and not re.search(r"\bventa", title, re.I):
        # listado home mezcla alquiler; skip en parser de venta
        pass  # still return; operation will mark Alquiler

    price = None
    currency = "USD"
    m = re.search(r"U\$S\s*([\d.]+)", html[:30000])
    if m:
        price = parse_price(m.group(1))
    if price is None:
        m = re.search(r"USD\s*([\d.]+)", html[:30000], re.I)
        if m:
            price = parse_price(m.group(1))
    if price is None:
        m = re.search(r"Gs\.?\s*([\d.]+)", html[:30000], re.I)
        if m:
            price = parse_price(m.group(1))
            currency = "PYG"

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
        r'src="(https?://[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        u = m.group(1)
        if "logo" in u.lower() or "icon" in u.lower():
            continue
        if u not in images:
            images.append(u)
        if len(images) >= 6:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Asunción"
    for c in ("luque", "san lorenzo", "fernando de la mora", "lambare", "capiata", "ciudad del este"):
        if c in blob:
            city = c.title()
            break

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
        province=city if city != "Asunción" else "Central",
        rooms=first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:amb|dorm|habit)", blob, re.I))),
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name="Nueva Alianza",
        extras={"country": "Paraguay"},
    )
