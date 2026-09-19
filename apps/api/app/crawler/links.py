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
    # robots.txt: Allow: /propiedades/*-ubicado-en-* ; Disallow: /*-ubicado-en-*
    # Solo aceptar fichas bajo /propiedades/ con el patrón ubicado-en.
    hrefs = re.findall(r'href="([^"]*?/propiedades/[^"]*?-ubicado-en-[^"]*?-\d{7,}\.html)"', html)
    if not hrefs:
        # Fallback: IDs largos bajo /propiedades/ (por si el slug varía)
        hrefs = re.findall(r'href="([^"]*?/propiedades/[^"]*?-\d{7,}\.html)"', html)
    out = []
    for h in hrefs:
        full = urljoin(base_url, h)
        # Descartar URLs con query params prohibidos por robots.txt
        if any(x in full for x in ("utm_", "n_src=", "gad_source=", "gclid=", "fbclid=", "duplicated=true", "labs=")):
            continue
        if "/propiedades/" in full and "-ubicado-en-" in full:
            out.append(full)
        elif "/propiedades/" in full:
            out.append(full)
    return _dedupe(out)


def _argenprop(html: str, base_url: str) -> list[str]:
    # Fichas terminan en "--<id numérico>"
    hrefs = re.findall(r'href="([^"]*--\d{5,})"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _cordobaprop(html: str, base_url: str) -> list[str]:
    # Patrón real confirmado 2026-09-14 contra HTML en vivo de
    # www.cordobaprop.com/propiedades/?operaciones=1&tipos=1:
    # https://www.cordobaprop.com/propiedad/<id>-<slug>
    # (el patrón "/propiedad-id-<N>-titulo-<slug>.html" pusheado antes
    # era incorrecto y por eso discover_detail_urls() devolvía 0 fichas)
    hrefs = re.findall(r'href="([^"]*/propiedad/\d+-[^"]*)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mendozaprop(html: str, base_url: str) -> list[str]:
    # Sitemap XML: solo venta (prefijo /venta-). Alquiler y home se descartan.
    if "<urlset" in html or "<sitemapindex" in html or html.lstrip().startswith("<?xml"):
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", html)
        out = []
        for loc in locs:
            loc = loc.strip()
            if "/venta-" in loc:
                out.append(loc)
        return _dedupe(out)
    # Fallback HTML (raro): /venta-.../ID
    hrefs = re.findall(r'href="([^"]*/venta-[^"]+/\d+)"', html)
    hrefs += re.findall(r'href="(/propiedades/\d+[^"]*)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mercado_unico(html: str, base_url: str) -> list[str]:
    # IDs tipo ObjectId de Mongo (24 hex chars) — aparecen en homepage
    hrefs = re.findall(r'href="(/propiedades/[a-f0-9]{24})"', html)
    hrefs += re.findall(r'href="(https://www\.mercado-unico\.com/propiedades/[a-f0-9]{24})"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _mercadolibre(html: str, base_url: str) -> list[str]:
    """Detalle MLA/MLM desde listado (AR + MX)."""
    hrefs = re.findall(
        r'href="(https?://(?:inmueble|casa|departamento|terreno|campo)\.mercadolibre\.com\.(?:ar|mx)/[^"]*ML[A-Z]-?\d+[^"]*)"',
        html,
    )
    hrefs += re.findall(r'href="(/(?:ML[A-Z]-?\d{8,14})[^"]*)"', html)
    ids = re.findall(
        r"(?:inmueble|casa|departamento|terreno|campo)\.mercadolibre\.com\.(?:ar|mx)/(ML[A-Z]-?\d+)",
        html,
    )
    ids += re.findall(r'href="/(ML[A-Z]-?\d{8,14})"', html)
    is_mx = ".com.mx" in base_url or "mercadolibre.com.mx" in html[:2000]
    out = [urljoin(base_url, h) for h in hrefs]
    for i in ids:
        mid = i if re.match(r"ML[A-Z]", i) else f"MLA-{i}"
        mid = re.sub(r"(ML[A-Z])-+", r"\1-", mid)
        host = "inmueble.mercadolibre.com.mx" if is_mx or mid.startswith("MLM") else "inmueble.mercadolibre.com.ar"
        out.append(f"https://{host}/{mid}")
    clean = []
    for u in out:
        u = u.split("#")[0].split("?")[0]
        if "mlstatic.com" in u:
            continue
        clean.append(u)
    return _dedupe(clean)


def _argencasas(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]*/propiedad-[^"?#]+)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _departamentosenpozo(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(/desarrollos-inmobiliarios/[a-z0-9\-]+/?)"', html)
    out = []
    for h in hrefs:
        if h.rstrip("/") == "/desarrollos-inmobiliarios":
            continue
        out.append(urljoin(base_url, h))
    return _dedupe(out)


def _bullano(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]*/campos/ficha/[^"]+\.html)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _grupoedisur(html: str, base_url: str) -> list[str]:
    """Proyectos / unidades bajo /desarrollos/... (absolutos o relativos)."""
    hrefs = re.findall(
        r'href="((?:https://www\.grupoedisur\.com\.ar)?/desarrollos/[a-z0-9\-/]+/?)"',
        html,
        re.I,
    )
    out: list[str] = []
    for h in hrefs:
        u = urljoin("https://www.grupoedisur.com.ar", h)
        # Saltar listados raíz
        path = u.rstrip("/").split("/desarrollos")[-1]
        if not path or path == "/":
            continue
        if path.rstrip("/") in ("/proyectos", "/desarrollos"):
            continue
        # Preferir fichas de profundidad >= 2 segmentos (ej. /casonas/torrentes)
        depth = [p for p in path.split("/") if p]
        if len(depth) < 2:
            continue
        out.append(u)
    return _dedupe(out)


def _inmoclick(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]+/inmuebles/\d+/ficha/[^"]+)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _inmoup(html: str, base_url: str) -> list[str]:
    # Patrón real: /{agency-id}-{slug}/inmuebles/{n}/ficha/{slug-detalle}
    hrefs = re.findall(r'href="([^"]+/inmuebles/\d+/ficha/[^"]+)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])


def _properati(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]*/detalle/[^"]+)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])



def _infocasas(html: str, base_url: str) -> list[str]:
    """InfoCasas: URLs en __NEXT_DATA__ o href absolutos con id numérico final."""
    import json
    urls: list[str] = []
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        blob = m.group(1)
        urls.extend(re.findall(r'https://www\.infocasas\.com\.(?:py|uy)/[^"\\]+/\d{6,}', blob))
        for rel in re.findall(r'"link"\s*:\s*"(/[^"]+/\d{6,})"', blob):
            urls.append(urljoin(base_url, rel))
    urls.extend(re.findall(r'href="(https://www\.infocasas\.com\.(?:py|uy)/[^"]+/\d{6,})"', html))
    return _dedupe(urls)


def _bienesonline(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href="(https://bienesonline\.ai/[^"]*/propiedad/\d+[^"]*)"', html)
    hrefs += re.findall(r'href="(/es/[^"]*/propiedad/\d+[^"]*)"', html)
    return _dedupe([urljoin(base_url, h) for h in hrefs])



def _tokko_agency(html: str, base_url: str) -> list[str]:
    from .parsers.tokko_agency import extract_detail_urls_tokko
    return extract_detail_urls_tokko(html, base_url)


def _agency_prop_uy(html: str, base_url: str) -> list[str]:
    from .parsers.agency_prop_uy import extract_detail_urls
    return extract_detail_urls(html, base_url)


def _agency_orangehome_mx(html: str, base_url: str) -> list[str]:
    from .parsers.agency_orangehome_mx import extract_detail_urls
    return extract_detail_urls(html, base_url)


def _agency_nuevaalianza_py(html: str, base_url: str) -> list[str]:
    from .parsers.agency_nuevaalianza_py import extract_detail_urls
    return extract_detail_urls(html, base_url)

EXTRACTORS = {
    "zonaprop": _zonaprop,
    "argenprop": _argenprop,
    "cordobaprop": _cordobaprop,
    "mendozaprop": _mendozaprop,
    "mercado_unico": _mercado_unico,
    "inmoclick": _inmoclick,
    "mercadolibre": _mercadolibre,
    "mercadolibre_mx": _mercadolibre,
    "properati": _properati,
    "inmoup": _inmoup,
    "infocasas_py": _infocasas,
    "infocasas_uy": _infocasas,
    "bienesonline": _bienesonline,
    "argencasas": _argencasas,
    "departamentosenpozo": _departamentosenpozo,
    "bullano": _bullano,
    "grupoedisur": _grupoedisur,
    "agency_paganini_ar": _tokko_agency,
    "agency_prey_ar": _tokko_agency,
    "agency_prop_uy": _agency_prop_uy,
    "agency_orangehome_mx": _agency_orangehome_mx,
    "agency_nuevaalianza_py": _agency_nuevaalianza_py,
}


def extract_detail_urls(source: str, html: str, base_url: str, limit: int = 40) -> list[str]:
    fn = EXTRACTORS.get(source)
    if not fn:
        raise KeyError(f"Sin extractor de links para fuente: {source}")
    return fn(html, base_url)[:limit]
