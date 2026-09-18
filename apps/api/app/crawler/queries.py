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
    """InmoUp — listados de venta por provincia (Cuyo + vecinos).
    Patrón: /departamentos-en-venta-en-mendoza — paginación ?page=N. Solo venta.
    """
    provincias = provincias or [
        "mendoza", "san-juan", "san-luis", "cordoba", "la-pampa", "neuquen",
    ]
    tipos = tipos or ["departamentos", "casas"]
    max_page = min(max_page, 8)
    for prov, tipo in product(provincias, tipos):
        base_url = f"https://inmoup.com.ar/{tipo}-en-venta-en-{prov}"
        for page in range(1, max_page + 1):
            yield base_url if page == 1 else f"{base_url}?page={page}"


def inmoclick_list_urls() -> Iterator[str]:
    """InmoClick — listados por provincia AR (HTML con hrefs /ficha/)."""
    paths = (
        "inmuebles-en-venta",
        "inmuebles-en-venta-en-capital-federal",
        "inmuebles-en-venta-en-buenos-aires",
        "inmuebles-en-venta-en-cordoba",
        "inmuebles-en-venta-en-santa-fe",
        "inmuebles-en-venta-en-rosario",
        "inmuebles-en-venta-en-mendoza",
        "inmuebles-en-venta-en-tucuman",
        "inmuebles-en-venta-en-entre-rios",
        "inmuebles-en-venta-en-salta",
        "inmuebles-en-venta-en-misiones",
        "inmuebles-en-venta-en-chaco",
        "inmuebles-en-venta-en-corrientes",
        "inmuebles-en-venta-en-santiago-del-estero",
        "inmuebles-en-venta-en-san-juan",
        "inmuebles-en-venta-en-jujuy",
        "inmuebles-en-venta-en-rio-negro",
        "inmuebles-en-venta-en-neuquen",
        "inmuebles-en-venta-en-formosa",
        "inmuebles-en-venta-en-chubut",
        "inmuebles-en-venta-en-san-luis",
        "inmuebles-en-venta-en-catamarca",
        "inmuebles-en-venta-en-la-rioja",
        "inmuebles-en-venta-en-la-pampa",
        "inmuebles-en-venta-en-santa-cruz",
        "inmuebles-en-venta-en-tierra-del-fuego",
    )
    for path in paths:
        yield f"https://www.inmoclick.com.ar/{path}"


def mercadolibre_list_urls() -> Iterator[str]:
    """ML Inmuebles — casas y deptos en venta, todas las provincias AR."""
    provincias = (
        "capital-federal",
        "buenos-aires",
        "cordoba",
        "santa-fe",
        "mendoza",
        "tucuman",
        "entre-rios",
        "salta",
        "misiones",
        "chaco",
        "corrientes",
        "santiago-del-estero",
        "san-juan",
        "jujuy",
        "rio-negro",
        "neuquen",
        "formosa",
        "chubut",
        "san-luis",
        "catamarca",
        "la-rioja",
        "la-pampa",
        "santa-cruz",
        "tierra-del-fuego",
    )
    for prov in provincias:
        yield f"https://inmuebles.mercadolibre.com.ar/casas/venta/{prov}/"
        yield f"https://inmuebles.mercadolibre.com.ar/departamentos/venta/{prov}/"


def infocasas_py_list_urls() -> Iterator[str]:
    """InfoCasas Paraguay — listados por ciudad (SSR + __NEXT_DATA__)."""
    for path in (
        "venta/inmuebles/asuncion",
        "venta/inmuebles/san-lorenzo",
        "venta/inmuebles/luque",
        "venta/inmuebles/ciudad-del-este",
        "venta/inmuebles/fernando-de-la-mora",
        "venta/inmuebles/lambare",
        "venta/inmuebles/encarnacion",
        "venta",
    ):
        yield f"https://www.infocasas.com.py/{path}"


def infocasas_uy_list_urls() -> Iterator[str]:
    """InfoCasas Uruguay — listados por ciudad / departamento."""
    for path in (
        "venta/inmuebles/montevideo",
        "venta/inmuebles/canelones",
        "venta/inmuebles/maldonado",
        "venta/inmuebles/colonia",
        "venta/inmuebles/salto",
        "venta/inmuebles/paysandu",
        "venta",
    ):
        yield f"https://www.infocasas.com.uy/{path}"


def bienesonline_list_urls() -> Iterator[str]:
    """BienesOnline AR — nacional + provincias con href /propiedad/{id}."""
    for path in (
        "es/argentina",
        "es/argentina/buenos-aires",
        "es/argentina/capital-federal",
        "es/argentina/cordoba",
        "es/argentina/santa-fe",
        "es/argentina/mendoza",
        "es/argentina/tucuman",
        "es/argentina/entre-rios",
        "es/argentina/salta",
        "es/argentina/misiones",
        "es/argentina/neuquen",
        "es/argentina/rio-negro",
        "es/argentina/chubut",
        "es/argentina/san-juan",
        "es/argentina/san-luis",
    ):
        yield f"https://bienesonline.ai/{path}"
