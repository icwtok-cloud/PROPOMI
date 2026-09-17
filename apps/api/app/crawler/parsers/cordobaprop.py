"""CordobaProp — JSON-LD Product + tabla HTML + array images en script."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "cordobaprop"


def parse_detail(html: str, url: str) -> RawListing | None:
    ld = None
    m = re.search(r'<script type="application/ld\+json">(\{.*?\})</script>', html, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
        except json.JSONDecodeError:
            ld = None

    title = ""
    price = None
    currency = "USD"
    description = ""
    images: list[str] = []

    if ld:
        title = ld.get("name") or ""
        description = strip_contact_leaks(ld.get("description"))
        offers = ld.get("offers") or {}
        price = parse_price(offers.get("price"))
        currency = offers.get("priceCurrency") or "USD"
        imgs = ld.get("image") or []
        if isinstance(imgs, str):
            imgs = [imgs]
        images = list(imgs)[:5]
        brand = (ld.get("brand") or {}).get("name") or ""
    else:
        brand = ""

    # Tabla info
    def cell(label: str) -> str | None:
        mm = re.search(rf"<th>{re.escape(label)}</th>\s*<td>([^<]+)</td>", html, re.I)
        return mm.group(1).strip() if mm else None

    address = cell("Dirección") or ""
    zone = cell("Barrio") or ""
    city = cell("Localidad") or "Cordoba"
    province = cell("Provincia") or "Córdoba"
    surface = parse_price(cell("Superficie total / terreno") or cell("Superficie cubierta"))
    surface_cov = parse_price(cell("Superficie cubierta"))
    bedrooms = first_int(cell("Dormitorios"))
    bathrooms = first_int(cell("Baños"))
    ptype = cell("Tipo de inmueble") or "Casa"
    origin = cell("Fecha de ingreso")
    external = cell("Código de referencia")
    # Patrón real confirmado 2026-09-15: /propiedad-id-<N>-titulo-<slug>.html
    # (antes se asumía /propiedad/<N>-<slug>, que nunca matcheaba)
    id_m = re.search(r"/propiedad-id-(\d+)-titulo-", url)
    if id_m:
        external = external or id_m.group(1)

    # images array in script
    if not images:
        im = re.search(r"const images = (\[.*?\]);", html, re.S)
        if im:
            try:
                images = json.loads(im.group(1).replace("\\/", "/"))[:5]
            except json.JSONDecodeError:
                pass

    h1 = re.search(r"<h1>([^<]+)</h1>", html)
    if h1 and not title:
        title = h1.group(1).strip()

    price_m = re.search(r'class="prop-price"[^>]*>\s*USD\s*([\d,]+)', html)
    if price_m and not price:
        price = parse_price(price_m.group(1))

    agency = brand
    am = re.search(r'font-weight:600[^>]*>([^<]+)</div>\s*<small[^>]*>Matrícula', html)
    if am:
        agency = am.group(1).strip()

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=str(external or ""),
        title=title,
        description=description or strip_contact_leaks(
            re.search(r"<h2>Descripción</h2>\s*<div[^>]*>(.*?)</div>", html, re.S)
            and re.sub(r"<[^>]+>", "", re.search(r"<h2>Descripción</h2>\s*<div[^>]*>(.*?)</div>", html, re.S).group(1))
            or ""
        ),
        price=price,
        currency=currency,
        zone=zone,
        city=city,
        province=province,
        address=address,
        surface=surface,
        surface_covered=surface_cov,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        rooms=bedrooms,
        property_type=ptype,
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=images,
        agency_name=agency,
        origin_published_at=origin,
    )
