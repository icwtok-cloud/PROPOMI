"""Brokers (brokers.com.py) — listado home + fichas /propiedad/{id}_{slug}/."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_brokers_py"
BASE = "https://www.brokers.com.py"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(https://(?:www\.)?brokers\.com\.py/propiedad/\d+_[^"]+)"', html)
    hrefs += re.findall(r'href="(/propiedad/\d+_[^"]+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url or BASE, h)
        low = full.lower()
        # Preferir venta; descartar alquiler puro en slug
        if re.search(r"(?:^|[_-])alquil", low) and "vendo" not in low and "venta" not in low:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_blob(blob: str) -> str:
    b = blob.lower()
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "deposito" in b or "depósito" in b or "galpon" in b:
        return "Local"
    if "local" in b or "oficina" in b or "comercial" in b:
        return "Local"
    if "casa" in b or "duplex" in b or "dúplex" in b:
        return "Casa"
    if "departamento" in b or "depto" in b or "dto" in b or "apto" in b:
        return "Departamento"
    return "Departamento"


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(r"/propiedad/(\d+)_", url)
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
        title = tm.group(1).split("&#8211;")[0].split("–")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1).replace("\\n", " "))
    if not desc:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        if dm:
            desc = strip_contact_leaks(dm.group(1))

    price = None
    currency = "USD"
    # USD first
    for pat in (r"USD\s*([\d.]+)", r"U\$S\s*([\d.]+)", r"US\$\s*([\d.]+)"):
        m = re.search(pat, html[:40000], re.I)
        if m:
            price = parse_price(m.group(1))
            break
    if price is None:
        # Guaraníes: gs. 4.700.000
        m = re.search(r"[Gg]s\.?\s*([\d.]+)", html[:40000])
        if m:
            price = parse_price(m.group(1))
            currency = "PYG"

    images: list[str] = []
    om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
    if om:
        images.append(om.group(1))
    for m in re.finditer(
        r'src="(https://[^"]+(?:blob\.core\.windows\.net|brokers)[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        if m.group(1) not in images:
            images.append(m.group(1))
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Asunción"
    for c in (
        "fernando de la mora", "fdo.mora", "fdo mora", "luque", "san lorenzo",
        "lambare", "capiata", "villa elisa", "ciudad del este", "encarnacion",
    ):
        if c in blob:
            city = (
                "Fernando de la Mora" if "mora" in c
                else c.replace("fdo.", "Fernando de la ").title()
            )
            if "mora" in c:
                city = "Fernando de la Mora"
            else:
                city = c.title()
            break

    # "Vendo ... con Renta" = venta de unidad rentada → Venta
    if re.search(r"\bvend[oa]", title, re.I) or "vendo" in url.lower():
        operation = "Venta"
    elif re.search(r"\balquil", title, re.I):
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
        province="Central" if city != "Asunción" else "Asunción",
        rooms=first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:dorm|habit|amb)", blob, re.I))),
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name="Brokers",
        extras={"country": "Paraguay"},
    )
