"""Parsers Tokko CMS (template cloudfront d1v2p1s05qqabi) — Paganini, Prey, etc.

Patrón de ficha: /propiedad/{slug}--{numeric_id}
Listado: /propiedades?operation[]=1 (venta) + ?page=N
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks


def _type_from_blob(blob: str) -> str:
    b = blob.lower()
    if "terreno" in b or "lote" in b:
        return "Terreno"
    if "campo" in b or "chacra" in b:
        return "Campo"
    if re.search(r"\bph\b|dúplex|duplex|triplex|tríplex", b):
        return "PH"
    if "local" in b or "comercial" in b:
        return "Local"
    if "oficina" in b:
        return "Oficina"
    if "casa" in b or "chalet" in b:
        return "Casa"
    return "Departamento"


def extract_detail_urls_tokko(html: str, base_url: str) -> list[str]:
    """Extrae /propiedad/{slug}--{id} del HTML de listado Tokko."""
    hrefs = re.findall(r'href="([^"]*/propiedad/[^"]+--\d+)"', html)
    hrefs += re.findall(r'href="(/propiedad/[^"]+--\d+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url, h)
        # Preferir venta; descartar alquiler puro si el slug lo dice
        low = full.lower()
        if "alquiler" in low and "venta" not in low:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def parse_detail_tokko(html: str, url: str, source_id: str, agency_name: str = "") -> RawListing | None:
    idm = re.search(r"--(\d+)/?$", url.rstrip("/"))
    external_id = idm.group(1) if idm else None

    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og:
        title = og.group(1).strip()
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).strip() if tm else ""
    if not title:
        h1 = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
        title = h1.group(1).strip() if h1 else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    # JSON embebido frecuente en Tokko
    pm = re.search(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    if pm:
        price = parse_price(pm.group(1))
    if price is None:
        for pat, cur in (
            (r"USD\s*([\d.,]+)", "USD"),
            (r"U\$S\s*([\d.,]+)", "USD"),
            (r"US\$\s*([\d.,]+)", "USD"),
            (r"ARS\s*([\d.,]+)", "ARS"),
            (r"\$\s*([\d.,]+)", "USD"),
        ):
            m = re.search(pat, html[:25000], re.I)
            if m:
                price = parse_price(m.group(1))
                currency = cur
                break
    cm = re.search(r'"currency"\s*:\s*"([^"]+)"', html, re.I)
    if cm:
        c = cm.group(1).upper().replace("U$S", "USD").replace("US$", "USD")
        if c in ("USD", "ARS", "EUR"):
            currency = c

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))
    if not desc:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        if dm:
            desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    for m in re.finditer(
        r'(https://d1v2p1s05qqabi\.cloudfront\.net/\d+/\d+\.(?:jpg|jpeg|webp|png))',
        html,
        re.I,
    ):
        if m.group(1) not in images:
            images.append(m.group(1))
        if len(images) >= 8:
            break
    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    # Geo heuristics from slug / title (Rosario focus for these agencies)
    blob = f"{url} {title} {desc}".lower()
    city = "Rosario" if "rosario" in blob else ""
    zone = ""
    for z in (
        "centro", "alberdi", "pichincha", "fisherton", "funes", "abasto",
        "martin", "lourdes", "belgrano", "republica de la sexta", "rep de la sexta",
        "zona rio", "facultades", "echesortu", "moderno",
    ):
        if z in blob:
            zone = z.title().replace("De La", "de la")
            break
    if not city and "funes" in blob:
        city = "Funes"

    rooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d)\s*(?:amb|dorm)", blob, re.I))
    )
    bedrooms = first_int(
        *(m.group(1) for m in re.finditer(r"(\d)\s*dorm", blob, re.I))
    )
    surface = None
    sm = re.search(r"(\d{2,4})\s*m(?:2|²)", blob, re.I)
    if sm:
        try:
            surface = float(sm.group(1))
        except ValueError:
            pass

    operation = detect_operation_from_signals(url=url, title=title, html=html) or "Venta"
    ptype = _type_from_blob(blob)

    return RawListing(
        source=source_id,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        zone=zone,
        city=city or "Rosario",
        province="Santa Fe",
        surface=surface,
        rooms=rooms,
        bedrooms=bedrooms,
        property_type=ptype,
        operation=operation,
        images=images[:5],
        agency_name=agency_name,
        extras={"country": "Argentina"},
    )


# --- Wrappers por source_id ---

def parse_detail_paganini(html: str, url: str) -> RawListing | None:
    return parse_detail_tokko(html, url, "agency_paganini_ar", "Paganini")


def parse_detail_prey(html: str, url: str) -> RawListing | None:
    return parse_detail_tokko(html, url, "agency_prey_ar", "Prey")


# --- Variante Tokko /p/{id}-{slug} (Hábitat Rosario, Newport UY, etc.) ---

def extract_detail_urls_tokko_p(html: str, base_url: str) -> list[str]:
    """Fichas /p/{numeric_id}-{slug} (template Tokko alternativo)."""
    hrefs = re.findall(r'href="(/p/\d+-[^"?#]+)"', html)
    hrefs += re.findall(r'href="(https?://[^"]+/p/\d+-[^"?#]+)"', html)
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        full = urljoin(base_url, h)
        low = full.lower()
        # Preferir venta; descartar alquiler puro en el slug
        if "alquiler" in low and "venta" not in low:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def parse_detail_tokko_p(
    html: str,
    url: str,
    source_id: str,
    agency_name: str = "",
    default_city: str = "",
    default_province: str = "",
    default_country: str = "Argentina",
) -> RawListing | None:
    idm = re.search(r"/p/(\d+)-", url)
    external_id = idm.group(1) if idm else None

    title = ""
    og = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if og:
        title = og.group(1).strip()
    if not title:
        tm = re.search(r"<title[^>]*>([^<]+)", html, re.I)
        title = tm.group(1).strip() if tm else ""
    if not title:
        h1 = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
        title = h1.group(1).strip() if h1 else ""
    if not title:
        return None
    title = re.sub(r"\s+", " ", title)[:180]

    price = None
    currency = "USD"
    # Formatos: USD97.000 | USD 97.000 | USD300\xa0000 (nbsp miles Tokko)
    chunk = html[:80000].replace("\xa0", " ").replace("\u00a0", " ")
    m = re.search(r"USD\s*([\d.]+(?:\s[\d]{3})*)", chunk, re.I)
    if m:
        raw = re.sub(r"[.\s]", "", m.group(1))
        try:
            price = float(raw)
        except ValueError:
            price = parse_price(m.group(1))
    if price is None:
        for pat, cur in (
            (r"U\$S\s*([\d.\s]+)", "USD"),
            (r"US\$\s*([\d.\s]+)", "USD"),
            (r"ARS\s*([\d.\s]+)", "ARS"),
            (r"UYU\s*([\d.\s]+)", "UYU"),
        ):
            mm = re.search(pat, chunk[:50000], re.I)
            if mm:
                raw = re.sub(r"[.\s]", "", mm.group(1))
                try:
                    price = float(raw)
                except ValueError:
                    price = parse_price(mm.group(1))
                currency = cur
                break

    desc = ""
    dm = re.search(r'property="og:description"\s+content="([^"]*)"', html)
    if dm:
        desc = strip_contact_leaks(dm.group(1))
    if not desc:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        if dm:
            desc = strip_contact_leaks(dm.group(1))

    images: list[str] = []
    for m in re.finditer(
        r'(https://d1v2p1s05qqabi\.cloudfront\.net/\d+/\d+\.(?:jpg|jpeg|webp|png))',
        html,
        re.I,
    ):
        if m.group(1) not in images:
            images.append(m.group(1))
        if len(images) >= 8:
            break
    if not images:
        om = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if om:
            images = [om.group(1)]

    blob = f"{url} {title} {desc}".lower()
    city = default_city
    zone = ""
    if default_country == "Argentina":
        if "rosario" in blob:
            city = "Rosario"
        elif "funes" in blob:
            city = "Funes"
        for z in (
            "centro", "alberdi", "pichincha", "fisherton", "funes", "abasto",
            "lourdes", "belgrano", "echesortu", "moderno", "facultades",
        ):
            if z in blob:
                zone = z.title()
                break
    elif default_country == "Uruguay":
        for c in (
            "montevideo", "pocitos", "punta carretas", "carrasco", "malvin",
            "ciudad vieja", "cordon", "cordón", "punta del este", "maldonado",
            "la barra", "jose ignacio", "josé ignacio", "colonia", "minas",
        ):
            if c in blob:
                city = c.replace("josé", "Jose").replace("cordón", "Cordon").title()
                city = city.replace("Jose Ignacio", "José Ignacio").replace("Cordon", "Cordón")
                break
        if not city:
            city = default_city or "Montevideo"

    rooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*(?:amb|dorm)", blob, re.I)))
    bedrooms = first_int(*(m.group(1) for m in re.finditer(r"(\d)\s*dorm", blob, re.I)))
    surface = None
    sm = re.search(r"(\d{2,4})\s*m(?:2|²)", blob, re.I)
    if sm:
        try:
            surface = float(sm.group(1))
        except ValueError:
            pass

    operation = detect_operation_from_signals(url=url, title=title, html=html) or "Venta"
    if "alquiler" in blob and "venta" not in blob:
        operation = "Alquiler"

    return RawListing(
        source=source_id,
        source_url=url,
        external_id=external_id,
        title=title,
        description=desc,
        price=price,
        currency=currency,
        zone=zone,
        city=city or default_city,
        province=default_province,
        surface=surface,
        rooms=rooms,
        bedrooms=bedrooms,
        property_type=_type_from_blob(blob),
        operation=operation,
        images=images[:5],
        agency_name=agency_name,
        extras={"country": default_country},
    )


def parse_detail_habitat(html: str, url: str) -> RawListing | None:
    return parse_detail_tokko_p(
        html, url,
        source_id="agency_habitat_ar",
        agency_name="Hábitat",
        default_city="Rosario",
        default_province="Santa Fe",
        default_country="Argentina",
    )


def parse_detail_newport(html: str, url: str) -> RawListing | None:
    return parse_detail_tokko_p(
        html, url,
        source_id="agency_newport_uy",
        agency_name="Newport",
        default_city="Montevideo",
        default_province="Montevideo",
        default_country="Uruguay",
    )
