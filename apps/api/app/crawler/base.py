"""Tipos y utilidades compartidas para parsers de fichas."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawListing:
    source: str
    source_url: str
    external_id: str | None = None
    title: str = ""
    description: str = ""
    price: float | None = None
    currency: str = "USD"
    zone: str = ""
    city: str = ""
    province: str = ""
    address: str = ""
    surface: float | None = None
    surface_covered: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking: bool | None = None
    credit: bool | None = None
    property_type: str = "Departamento"
    operation: str = "Venta"
    images: list[str] = field(default_factory=list)
    lat: float | None = None
    lng: float | None = None
    agency_name: str = ""
    agency_phone: str = ""
    origin_published_at: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != "" and v != []}


PHONE_RE = re.compile(
    r"(?:(?:\+?54|54)?[\s\-\.]?)?(?:9[\s\-\.]?)?(?:\(?\d{2,4}\)?[\s\-\.]?)?\d{3,4}[\s\-\.]?\d{3,4}"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.I)
WHATSAPP_RE = re.compile(r"whatsapp|wa\.me|api\.whatsapp", re.I)


def strip_contact_leaks(text: str | None) -> str:
    """Sanitiza descripción: quita teléfonos, emails, URLs y menciones WA."""
    if not text:
        return ""
    out = text
    out = EMAIL_RE.sub("[dato de contacto oculto]", out)
    out = URL_RE.sub("[enlace oculto]", out)
    out = WHATSAPP_RE.sub("[contacto oculto]", out)
    out = PHONE_RE.sub("[dato de contacto oculto]", out)
    return out.strip()


def parse_price(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).replace(".", "").replace(",", ".").strip()
    s = re.sub(r"[^\d.]", "", s)
    try:
        return float(s) if s else None
    except ValueError:
        return None


def first_int(*vals: Any) -> int | None:
    for v in vals:
        if v is None:
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            m = re.search(r"\d+", str(v))
            if m:
                return int(m.group(0))
    return None
