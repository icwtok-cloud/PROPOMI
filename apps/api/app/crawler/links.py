"""Extrae URLs de fichas individuales desde el HTML de una página de listado.

⚠️ Patrones basados en las convenciones de URL de cada portal (confirmadas
en las fichas de ejemplo analizadas), pero NO validados contra HTML real de
listado en todos los casos (solo teníamos fichas de detalle de referencia,
no listados completos). Antes de activar un source en producción, correr
`extract_detail_urls` contra un listado real guardado y confirmar que
devuelve URLs de fichas y no ruido (nav, footer, ads, etc.) — mismo
criterio que ya usa selectors.py para las fuentes existentes.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin


def _dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _zonaprop(html: str, base_url: str) -> list[str]:
    # Fichas terminan en un ID numérico largo + .html
    hrefs = re.findall(r'href="([^"]+-\d{7,}\.html)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _argenprop(html: str, base_url: str) -> list[str]:
    # Fichas terminan en "--<id numérico>"
    hrefs = re.findall(r'href="([^"]*--\d{5,})"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _cordobaprop(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(/propiedad/\d+-[^"]*)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mendozaprop(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(/propiedades/\d+[^"]*)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mercado_unico(html: str, base_url: str) -> list[str]:
    # IDs tipo ObjectId de Mongo (24 hex chars)
    hrefs = re.findall(r'href="(/propiedades/[a-f0-9]{24})"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mercadolibre(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(https?://[^"]*MLA-?\d{8,}[^"]*)"', html)
    return _dedupe(hrefs)


def _properati(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]*/detalle/[^"]+)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


EXTRACTORS = {
    "zonaprop": _zonaprop,
    "argenprop": _argenprop,
    "cordobaprop": _cordobaprop,
    "mendozaprop": _mendozaprop,
    "mercado_unico": _mercado_unico,
    "mercadolibre": _mercadolibre,
    "properati": _properati,
}


def extract_detail_urls(source: str, html: str, base_url: str, limit: int = 40) -> list[str]:
    fn = EXTRACTORS.get(source)
    if not fn:
        raise KeyError(f"Sin extractor de links para fuente: {source}")
    return fn(html, base_url)[:limit]
