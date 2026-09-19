"""PROP (prop.com.uy) — listado comprar + fichas /propiedades/venta-de-...-pNNNNNN."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "agency_prop_uy"


def extract_detail_urls(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(
        r'href="(https://prop\.com\.uy/propiedades/[^"]+-p\d+)"',
        html,
    )
    hrefs += re.findall(r'href="(/propiedades/[^"]+-p\d+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url, h)
        low = full.lower()
        if "alquilar" in low or "alquiler" in low:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _type_from_blob(blob: str) -> str:
    b = blob.lower()
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "chacra" in b or "campo" in b:
        return "Campo"
    if "casa" in b:
        return "Casa"
    if "local" in b or "oficina" in b:
        return "Local"
    return "Departamento"  # UY: apartamento → Departamento canónico


def parse_detail(html: str, url: str) -> RawListing | None:
    idm = re.search(r"-p(\d+)/?$", url.rstrip("/"), re.I)
    external_id = idm.group(1) if idm else None

    title = ""
    h1 = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
    if h1:
        title = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
    if not title:
        og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        title = og.group(1).strip() if og else ""
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).split("|")[0].strip() if tm else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    for pat in (
        r"USD\s*([\d.]+)",
        r"U\$S\s*([\d.]+)",
        r"US\$\s*([\d.]+)",
    ):
        m = re.search(pat, html[:30000], re.I)
        if m:
            price = parse_price(m.group(1))
            break
    if price is None:
        m = re.search(r"\$U\s*([\d.]+)", html[:30000])
        if m:
            price = parse_price(m.group(1))
            currency = "UYU"

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))
    if not desc:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        if dm:
            desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    for m in re.finditer(r'property="og:image"\s+content="([^"]+)"', html):
        if m.group(1) not in images:
            images.append(m.group(1))
    for m in re.finditer(
        r'src="(https://[^"]+(?:prop\.com\.uy|cloudfront|amazonaws)[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        html,
        re.I,
    ):
        u = m.group(1)
        if u not in images and "logo" not in u.lower():
            images.append(u)
        if len(images) >= 8:
            break

    blob = f"{url} {title} {desc}".lower()
    city = "Montevideo"
    for c in ("punta del este", "maldonado", "canelones", "colonia", "salto", "paysandu"):
        if c in blob:
            city = c.title()
            break
    zone = ""
    for z in (
        "cordón", "cordon", "pocitos", "carrasco", "centro", "la blanqueada",
        "parque batlle", "malvín", "malvin", "buceo", "palermo", "barrio sur",
        "ciudad vieja", "tres cruces", "prado", "goes",
    ):
        if z in blob:
            zone = z.replace("cordon", "Cordón").title() if z != "cordón" else "Cordón"
            break

    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:amb|dorm|dormitorio)", blob, re.I)))
    if "monoambiente" in blob:
        rooms = rooms or 1
        bedrooms = 0
    else:
        bedrooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*dorm", blob, re.I)))

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
        province=city if city != "Montevideo" else "Montevideo",
        rooms=rooms,
        bedrooms=bedrooms if "monoambiente" not in blob else 0,
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name="PROP",
        extras={"country": "Uruguay"},
    )
