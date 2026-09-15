"""Generadores de URLs de listado segmentadas (respetar robots: páginas 1–5 ZP, etc.)."""
from __future__ import annotations

from itertools import product
from typing import Iterator
from urllib.parse import urlencode


# --- ZonaProp (páginas 1–5 por combinación) ---
ZP_BARRIOS_CABA = [
    "caballito", "palermo", "belgrano", "recoleta", "villa-crespo",
    "almagro", "nunez", "colegiales", "villa-urquiza", "flores",
]
ZP_TIPOS = ["departamentos", "casas", "ph"]
ZP_OPERACION = "venta"


def zonaprop_list_urls(barrios: list[str] | None = None, tipos: list[str] | None = None, max_page: int = 5) -> Iterator[str]:
    barrios = barrios or ZP_BARRIOS_CABA
    tipos = tipos or ZP_TIPOS
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
    # operaciones=1 venta, tipos=1 casa, 2 depto
    tipos = tipos or [1, 2]
    for t in tipos:
        for page in range(1, max_page + 1):
            q = urlencode({"operaciones": 1, "tipos": t, "page": page})
            yield f"https://cordobaprop.com/propiedades/?{q}"


def mendozaprop_list_urls(regions: list[str] | None = None) -> Iterator[str]:
    regions = regions or ["mendoza", "guaymallen", "godoycruz", "maipu", "lujandecuyo"]
    for r in regions:
        yield f"https://www.mendozaprop.com/propiedades?region={r}"


def mercado_unico_list_urls() -> Iterator[str]:
    yield "https://www.mercado-unico.com/propiedades"
    # ampliar con filtros de ciudad cuando se confirme robots
