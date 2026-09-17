"""Tipos y utilidades compartidas para parsers de fichas."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("propomi.crawler")


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

_ALQUILER_KEYS = ("alquiler", "renta", "rent", "lease", "temporal")
_VENTA_KEYS = ("venta", "sale", "comprar", "buy", "compra")


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


def _norm_op(text: str | None) -> str | None:
    """Normaliza texto libre a 'Venta' | 'Alquiler' | None. Alquiler tiene prioridad."""
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    if any(k in t for k in _ALQUILER_KEYS):
        return "Alquiler"
    if any(k in t for k in _VENTA_KEYS):
        return "Venta"
    return None


def _operation_from_url(url: str) -> str | None:
    """Heurística de path/query usada por portales AR/UY/PY."""
    u = (url or "").lower()
    if re.search(r"(/|\?|&|=)(alquiler|rent|renta)([/\-?]|$)", u):
        return "Alquiler"
    if re.search(r"(/|\?|&|=)(venta|sale)([/\-?]|$)", u):
        return "Venta"
    if (
        "-en-alquiler" in u
        or "/en-alquiler" in u
        or "/alquiler-" in u
        or "operaciones=2" in u
    ):
        return "Alquiler"
    if (
        "-en-venta" in u
        or "/en-venta" in u
        or "/venta-" in u
        or "operaciones=1" in u
    ):
        return "Venta"
    return None


def _all_ld_json(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend([x for x in data if isinstance(x, dict)])
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                out.extend([x for x in data["@graph"] if isinstance(x, dict)])
            else:
                out.append(data)
    return out


def _operation_from_json_ld(html: str) -> str | None:
    """Extrae operación de JSON-LD: businessFunction, BreadcrumbList, additionalType."""
    for obj in _all_ld_json(html):
        # BreadcrumbList (MercadoLibre Inmuebles: item.name = Venta|Alquiler)
        if obj.get("@type") == "BreadcrumbList":
            for el in obj.get("itemListElement") or []:
                if not isinstance(el, dict):
                    continue
                item = el.get("item") if isinstance(el.get("item"), dict) else el
                name = str((item or {}).get("name") or "")
                op = _norm_op(name)
                if op:
                    return op
                iid = str((item or {}).get("@id") or "")
                op = _operation_from_url(iid)
                if op:
                    return op

        bf = obj.get("businessFunction") or obj.get("additionalType") or ""
        if isinstance(bf, list):
            bf = " ".join(str(x) for x in bf)
        op = _norm_op(str(bf))
        if op:
            return op

        # Offer / RealEstateListing a veces traen name con operación
        for key in ("name", "description", "category"):
            op = _norm_op(str(obj.get(key) or ""))
            if op:
                return op
    return None


def _operation_from_embedded_json(html: str) -> str | None:
    """Busca claves típicas en blobs embebidos (NUXT, avisoInfo, melidata, etc.)."""
    patterns = (
        r'"operacion"\s*:\s*"([^"]+)"',
        r'"operation"\s*:\s*"([^"]+)"',
        r'"operation_type"\s*:\s*"([^"]+)"',
        r'"tipoOperacion"\s*:\s*"([^"]+)"',
        r'"tipo_operacion"\s*:\s*"([^"]+)"',
        r'"transaction_type"\s*:\s*"([^"]+)"',
        r'"operationType"\s*:\s*"([^"]+)"',
        r'"realEstateBusiness"\s*:\s*"([^"]+)"',
    )
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            op = _norm_op(m.group(1))
            if op:
                return op

    # operationId numérico (ZonaProp histórico: 1=venta 2=alquiler — solo si hay más señal)
    m = re.search(r'"operationId"\s*:\s*(\d+)', html)
    if m:
        # No asumir solo por id; dejar a otros canales
        pass

    # melidata / category_id con texto
    m = re.search(r'"category_id"\s*:\s*"([^"]+)"', html)
    if m:
        op = _norm_op(m.group(1))
        if op:
            return op

    return None


def detect_operation_from_signals(
    *,
    url: str = "",
    html: str = "",
    title: str = "",
    embedded: dict[str, Any] | None = None,
) -> str:
    """Detecta Venta|Alquiler con prioridad de señales.

    Orden:
      1. Campos explícitos en dict embebido (si se pasa)
      2. JSON embebido en HTML (operacion, operation_type, …)
      3. JSON-LD (businessFunction, BreadcrumbList)
      4. Path/query de la URL
      5. Título (og:title / <title>)
      6. Default "Venta" + warning (catálogo es solo Venta)

    Alquiler tiene prioridad semántica sobre Venta en normalización de texto.
    """
    # 1) dict embebido explícito
    if embedded:
        for key in (
            "operacion",
            "operation",
            "operation_type",
            "tipoOperacion",
            "tipo_operacion",
            "transaction_type",
            "operationType",
        ):
            val = embedded.get(key)
            if val is not None:
                op = _norm_op(str(val))
                if op:
                    return op

    if html:
        # 2) JSON embebido
        op = _operation_from_embedded_json(html)
        if op:
            return op
        # 3) JSON-LD / Breadcrumb
        op = _operation_from_json_ld(html)
        if op:
            return op

    # 4) URL
    op = _operation_from_url(url)
    if op:
        return op

    # 5) título
    if not title and html:
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.I)
        if m:
            title = m.group(1)
        else:
            m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
            if m:
                title = m.group(1)
    op = _norm_op(title)
    if op:
        return op

    logger.warning(
        "detect_operation_from_signals: sin señal de operación, default Venta url=%s",
        (url or "")[:120],
    )
    return "Venta"
