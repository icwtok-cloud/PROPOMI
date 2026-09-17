"""InmoUp (inmoup.com.ar) — JSON-LD schema.org RealEstateListing / Accommodation."""
from __future__ import annotations

import json
import re
from typing import Any

from ..base import RawListing, detect_operation_from_signals, first_int, parse_price, strip_contact_leaks

SOURCE = "inmoup"


def _schema_graph(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(
        r'<script[^>]*>\s*(\{"@context":"https://schema\.org".*?\})\s*</script>',
        html,
        re.S,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "@graph" in data:
            out.extend(x for x in data["@graph"] if isinstance(x, dict))
        elif isinstance(data, dict):
            out.append(data)
    return out


def parse_detail(html: str, url: str) -> RawListing | None:
    graph = _schema_graph(html)
    listing = next(
        (
            x
            for x in graph
            if any(
                t in (x.get("@type") if isinstance(x.get("@type"), list) else [x.get("@type")])
                for t in ("RealEstateListing", "Accommodation", "Apartment", "House", "Product")
            )
        ),
        None,
    )

    title = ""
    description = ""
    price = None
    currency = "USD"
    rooms = bedrooms = bathrooms = None
    surface = None
    address = zone = city = ""
    images: list[str] = []
    phone = ""

    if listing:
        title = (listing.get("name") or "")[:180]
        description = strip_contact_leaks(listing.get("description") or "")
        img = listing.get("image")
        if isinstance(img, list):
            images = [u for u in img if isinstance(u, str)][:5]
        elif isinstance(img, str):
            images = [img]
        offers = listing.get("offers") or {}
        if isinstance(offers, dict):
            price = parse_price(offers.get("price"))
            currency = offers.get("priceCurrency") or currency
        addr = listing.get("address") or {}
        if isinstance(addr, dict):
            address = addr.get("streetAddress") or ""
            city = addr.get("addressLocality") or ""
            zone = addr.get("addressRegion") or city
        for av in listing.get("additionalProperty") or []:
            if not isinstance(av, dict):
                continue
            name = (av.get("name") or "").lower()
            val = av.get("value")
            if "superficie" in name or "m2" in name:
                surface = parse_price(val) or surface
            elif "ambiente" in name or "room" in name:
                rooms = first_int(val) or rooms
            elif "dormitorio" in name or "bedroom" in name:
                bedrooms = first_int(val) or bedrooms
            elif "baño" in name or "bath" in name:
                bathrooms = first_int(val) or bathrooms

    if not title:
        tm = re.search(r"<title>([^|<]+)", html)
        title = (tm.group(1).strip() if tm else "")[:180]
    if not description:
        dm = re.search(r'name="description"\s+content="([^"]*)"', html)
        description = strip_contact_leaks(dm.group(1) if dm else "")
    if not images:
        for om in re.finditer(r'property="og:image"[^>]+content="([^"]+)"', html):
            images.append(om.group(1))
            if len(images) >= 5:
                break
    if price is None:
        om = re.search(r'og:title"[^>]+content="[^"]*USD\s*([\d\.]+)', html)
        if om:
            price = parse_price(om.group(1).replace(".", ""))
        else:
            for pm in re.finditer(r'"price"\s*:\s*(\d{4,})', html):
                price = parse_price(pm.group(1))
                if price and price > 5000:
                    break

    # zona/ciudad desde URL o título
    if not city:
        for b in ("Mendoza", "Luján de Cuyo", "Godoy Cruz", "Guaymallén", "Maipú", "San Rafael", "San Juan", "San Luis"):
            if b.lower() in html.lower():
                city = b
                zone = zone or b
                break
    if not zone:
        zone = city or "Mendoza"

    external = None
    em = re.search(r"/inmuebles/(\d+)/ficha/", url)
    if em:
        external = em.group(1)

    return RawListing(
        source=SOURCE,
        source_url=url,
        external_id=external,
        title=title,
        description=description,
        price=price,
        currency=currency,
        zone=zone,
        city=city or "Mendoza",
        province="Mendoza",
        address=address,
        surface=surface,
        rooms=rooms or bedrooms,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        property_type="Departamento",
        operation=detect_operation_from_signals(url=url, html=html, title=title),
        images=images,
        agency_phone=phone,
    )
