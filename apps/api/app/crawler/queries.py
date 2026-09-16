"""Generadores de URLs de listado segmentadas (respetar robots: páginas 1–5 ZP, etc.)."""
from __future__ import annotations

from itertools import product
from typing import Iterator
from urllib.parse import urlencode


# --- ZonaProp (páginas 1–5; robots.txt permite solo hasta página 5) ---
# Piloto: Caballito, CABA, solo venta. Sin query params prohibidos (utm_*,
# n_src=, gad_source=, gclid=, fbclid=, duplicated=true, labs=).
ZP_BARRIOS_PILOTO = ["caballito"]
ZP_TIPOS = ["departamentos", "casas", "ph"]
ZP_OPERACION = "venta"


def zonaprop_list_urls(barrios: list[str] | None = None, tipos: list[str] | None = None, max_page: int = 5) -> Iterator[str]:
    """URLs de listado dentro de lo permitido por robots.txt de ZonaProp.
    Página 1 implícita; páginas 2-5 con -pagina-N.html. max_page cap a 5."""
    barrios = barrios or ZP_BARRIOS_PILOTO
    tipos = tipos or ZP_TIPOS
    max_page = min(max_page, 5)
    for barrio, tipo in product(barrios, tipos):
        for page in range(1, max_page + 1):
            # patrón típico ZP: /departamentos-venta-caballito.html o con -pagina-2
            if page == 1:
                yield f"https://www.zonaprop.com.ar/{tipo}-{ZP_OPERACION}-{barrio}.html"
            else:
                yield f"https://www.zonaprop.com.ar/{tipo}-{ZP_OPERACION}-{barrio}-pagina-{page}.html"


def argenprop_list_urls(zonas: list[str] | None = None, max_page: int = 5) -> Iterator[str]:
    # Una URL por filtro; paginación ?pagina-N
    zonas = zonas or ["olivos", "caballito", "palermo", "belgrano"]
    for zona in zonas:
        for page in range(1, max_page + 1):
            base = f"https://www.argenprop.com/departamento-venta-barrio-{zona}"
            yield base if page == 1 else f"{base}?pagina-{page}"


def cordobaprop_list_urls(tipos: list[int] | None = None, max_page: int = 10) -> Iterator[str]:
    # operaciones=1 venta, tipos=1 casa, 2 depto.
    # Confirmado 2026-09-14 contra HTML real:
    # - Requiere viewtype=list: sin este parámetro, las tarjetas de propiedad
    #   se renderizan sin <a href> navegable en el HTML servido (van por JS),
    #   por eso discover_detail_urls() encontraba 0 fichas.
    # - Requiere dominio www.cordobaprop.com (el listado sin viewtype=list
    #   en cordobaprop.com sin www a veces cayó en 0 resultados / tipo por
    #   defecto incorrecto en pruebas manuales).
    # - La paginación real es por offset (24 resultados por página), no por
    #   un parámetro "page" (que el sitio ignora silenciosamente).
    PAGE_SIZE = 24
    tipos = tipos or [1, 2]
    for t in tipos:
        for page in range(max_page):
            q = urlencode({
                "operaciones": 1,
                "tipos": t,
                "viewtype": "list",
                "offset": page * PAGE_SIZE,
            })
            yield f"https://www.cordobaprop.com/propiedades/?{q}"


def mendozaprop_list_urls(regions: list[str] | None = None) -> Iterator[str]:
    """Discovery vía sitemap oficial (listado SPA no expone hrefs estáticos).
    Solo se indexan URLs de venta; alquiler se filtra en links.py.
    Confirmado 2026-09-15: sitemap.xml ~11k locs, HTML de ficha con __NEXT_DATA__.
    """
    yield "https://www.mendozaprop.com/sitemap.xml"


def mercado_unico_list_urls() -> Iterator[str]:
    """Homepage expone fichas en HTML (el listado /propiedades es SPA vacío).
    Confirmado 2026-09-15: href /propiedades/{ObjectId 24 hex}.
    """
    yield "https://www.mercado-unico.com/"
    yield "https://www.mercado-unico.com/propiedades"


def inmoup_list_urls(provincias: list[str] | None = None, tipos: list[str] | None = None, max_page: int = 5) -> Iterator[str]:
    """InmoUp — listados de venta por provincia (Mendoza foco piloto Cuyo).
    Patrón real confirmado 2026-09-15: /departamentos-en-venta-en-mendoza
    Paginación: ?page=N (1-based). Solo venta, nunca alquiler.
    """
    provincias = provincias or ["mendoza"]
    tipos = tipos or ["departamentos", "casas"]
    max_page = min(max_page, 5)
    for prov, tipo in product(provincias, tipos):
        base = f"https://inmoup.com.ar/{tipo}-en-venta-en-{prov}"
        for page in range(1, max_page + 1):
            yield base if page == 1 else f"{base}?page={page}"


def inmoclick_list_urls() -> Iterator[str]:
    """InmoClick — listados por provincia (HTML con hrefs /ficha/)."""
    for path in (
        "inmuebles-en-venta-en-cordoba",
        "inmuebles-en-venta-en-mendoza",
        "inmuebles-en-venta-en-capital-federal",
        "inmuebles-en-venta-en-buenos-aires",
        "inmuebles-en-venta-en-santa-fe",
        "inmuebles-en-venta-en-rosario",
        "inmuebles-en-venta",
    ):
        yield f"https://www.inmoclick.com.ar/{path}"


def mercadolibre_list_urls() -> Iterator[str]:
    """ML Inmuebles — casas y deptos en venta por provincia piloto."""
    for prov in ("cordoba", "mendoza", "santa-fe", "buenos-aires"):
        yield f"https://inmuebles.mercadolibre.com.ar/casas/venta/{prov}/"
        yield f"https://inmuebles.mercadolibre.com.ar/departamentos/venta/{prov}/"


def infocasas_py_list_urls() -> Iterator[str]:
    """InfoCasas Paraguay — listados por ciudad principal (SSR + __NEXT_DATA__)."""
    for path in (
        "venta/inmuebles/asuncion",
        "venta/inmuebles/san-lorenzo",
        "venta/inmuebles/luque",
        "venta/inmuebles/ciudad-del-este",
        "venta",
    ):
        yield f"https://www.infocasas.com.py/{path}"


def infocasas_uy_list_urls() -> Iterator[str]:
    """InfoCasas Uruguay — listados por ciudad principal."""
    for path in (
        "venta/inmuebles/montevideo",
        "venta/inmuebles/canelones",
        "venta/inmuebles/maldonado",
        "venta",
    ):
        yield f"https://www.infocasas.com.uy/{path}"


def bienesonline_list_urls() -> Iterator[str]:
    """BienesOnline AR — listado nacional + provinciales con href /propiedad/{id}."""
    for path in (
        "es/argentina",
        "es/argentina/buenos-aires",
        "es/argentina/cordoba",
        "es/argentina/santa-fe",
        "es/argentina/mendoza",
    ):
        yield f"https://bienesonline.ai/{path}"
