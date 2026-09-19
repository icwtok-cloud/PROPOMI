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
    """ML Inmuebles AR — casas, deptos, PH, terrenos, campos (24 provincias).

    Paginación ML: offset 48 ítems → `_Desde_49`, `_Desde_97`, `_Desde_145`
    (4 páginas por combo provincia×tipo). El cursor de runner recorta por
    MAX_LIST_PAGES / MAX_DETAILS para no saturar una sola corrida.
    """
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
    tipos = ("casas", "departamentos", "ph", "terrenos", "campos")
    # page offsets ML (1-based item index)
    offsets = ("", "_Desde_49", "_Desde_97", "_Desde_145")
    for prov in provincias:
        for tipo in tipos:
            base = f"https://inmuebles.mercadolibre.com.ar/{tipo}/venta/{prov}"
            for off in offsets:
                yield f"{base}/{off}" if off else f"{base}/"


def mercadolibre_mx_list_urls() -> Iterator[str]:
    """ML Inmuebles México — cobertura amplia de estados + tipos + paginación."""
    estados = (
        "distrito-federal",
        "estado-de-mexico",
        "jalisco",
        "nuevo-leon",
        "queretaro",
        "puebla",
        "guanajuato",
        "yucatan",
        "quintana-roo",
        "baja-california",
        "baja-california-sur",
        "veracruz",
        "chihuahua",
        "coahuila",
        "michoacan",
        "morelos",
        "hidalgo",
        "aguascalientes",
        "san-luis-potosi",
        "tamaulipas",
        "sonora",
        "sinaloa",
        "tabasco",
        "oaxaca",
        "chiapas",
        "guerrero",
        "durango",
        "nayarit",
        "colima",
        "tlaxcala",
        "campeche",
        "zacatecas",
    )
    tipos = ("casas", "departamentos", "terrenos", "locales-comerciales", "oficinas")
    offsets = ("", "_Desde_49", "_Desde_97")
    for est in estados:
        for tipo in tipos:
            base = f"https://inmuebles.mercadolibre.com.mx/{tipo}/venta/{est}"
            for off in offsets:
                yield f"{base}/{off}" if off else f"{base}/"


def argencasas_list_urls() -> Iterator[str]:
    """Argencasas — venta nacional + paginación amplia por tipo."""
    yield "https://www.argencasas.com/venta"
    for page in range(2, 61):
        yield f"https://www.argencasas.com/motor/props.php?superoper=0&page={page}"
    for tipo in ("casas", "departamentos", "ph", "locales", "terrenos", "campos", "quintas"):
        yield f"https://www.argencasas.com/venta/{tipo}"
        for page in range(2, 11):
            yield f"https://www.argencasas.com/venta/{tipo}?page={page}"


def departamentosenpozo_list_urls() -> Iterator[str]:
    """Catálogo de desarrollos en pozo (CABA/GBA) — una página trae ~800 links."""
    yield "https://departamentosenpozo.com.ar/desarrollos-inmobiliarios/"
    yield "https://departamentosenpozo.com.ar/"


def bullano_list_urls() -> Iterator[str]:
    """Bullano — campos y chacras en venta (nacional + provincias)."""
    for path in (
        "campos/venta--chacra.html",
        "campos/venta.html",
        "campos/venta--chacra--dueno-directo.html",
        "campos/venta--chacra--inmobiliaria.html",
        "campos/venta--chacra--buenos-aires.html",
        "campos/venta--chacra--cordoba.html",
        "campos/venta--chacra--mendoza.html",
        "campos/venta--chacra--santa-fe.html",
        "campos/venta--chacra--misiones.html",
        "campos/venta--chacra--entre-rios.html",
        "campos/venta--chacra--la-pampa.html",
        "campos/venta--chacra--san-luis.html",
        "campos/venta--chacra--rio-negro.html",
        "campos/venta--chacra--neuquen.html",
        "campos/venta--chacra--chubut.html",
        "campos/venta--chacra--salta.html",
        "campos/venta--chacra--tucuman.html",
        "campos/venta--chacra--corrientes.html",
    ):
        yield f"https://www.bullano.com.ar/{path}"


def infocasas_py_list_urls() -> Iterator[str]:
    """InfoCasas Paraguay — listados por ciudad + tipos + páginas (?page=N)."""
    paths = (
        "venta/inmuebles/asuncion",
        "venta/inmuebles/san-lorenzo",
        "venta/inmuebles/luque",
        "venta/inmuebles/ciudad-del-este",
        "venta/inmuebles/fernando-de-la-mora",
        "venta/inmuebles/lambare",
        "venta/inmuebles/encarnacion",
        "venta/inmuebles/capiata",
        "venta/inmuebles/nemby",
        "venta/inmuebles/mariano-roque-alonso",
        "venta/inmuebles/villa-elisa",
        "venta/inmuebles/pedro-juan-caballero",
        "venta/inmuebles/itaugua",
        "venta/casas",
        "venta/departamentos",
        "venta/terrenos",
        "venta",
    )
    for path in paths:
        yield f"https://www.infocasas.com.py/{path}"
        for page in range(2, 6):
            yield f"https://www.infocasas.com.py/{path}?page={page}"


def infocasas_uy_list_urls() -> Iterator[str]:
    """InfoCasas Uruguay — listados por ciudad / departamento + tipos + páginas."""
    paths = (
        "venta/inmuebles/montevideo",
        "venta/inmuebles/canelones",
        "venta/inmuebles/maldonado",
        "venta/inmuebles/colonia",
        "venta/inmuebles/salto",
        "venta/inmuebles/paysandu",
        "venta/inmuebles/rocha",
        "venta/inmuebles/soriano",
        "venta/inmuebles/florida",
        "venta/inmuebles/san-jose",
        "venta/inmuebles/rivera",
        "venta/inmuebles/tacuarembo",
        "venta/casas",
        "venta/apartamentos",
        "venta/terrenos",
        "venta",
    )
    for path in paths:
        yield f"https://www.infocasas.com.uy/{path}"
        for page in range(2, 6):
            yield f"https://www.infocasas.com.uy/{path}?page={page}"


def grupoedisur_list_urls() -> Iterator[str]:
    """Grupo Edisur (Córdoba) — catálogo de desarrollos / pozo."""
    yield "https://www.grupoedisur.com.ar/desarrollos/"
    yield "https://www.grupoedisur.com.ar/desarrollos/proyectos/"
    yield "https://www.edisur.com.ar/proyectos"
    yield "https://www.edisur.com.ar/"


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


# --- Agencias TIER A (2026-09-19) ---

def agency_paganini_ar_list_urls() -> Iterator[str]:
    """Paganini (Rosario) — Tokko; operation[]=1 = venta."""
    yield "https://paganini.com.ar/propiedades?operation[]=1"
    for page in range(2, 8):
        yield f"https://paganini.com.ar/propiedades?operation[]=1&page={page}"


def agency_prey_ar_list_urls() -> Iterator[str]:
    """Prey (Rosario) — Tokko; catálogo + venta."""
    yield "https://preypropiedades.com/propiedades"
    yield "https://www.preypropiedades.com/Venta"
    for page in range(2, 8):
        yield f"https://preypropiedades.com/propiedades?page={page}"


def agency_prop_uy_list_urls() -> Iterator[str]:
    """PROP Uruguay — solo comprar (venta)."""
    yield "https://prop.com.uy/propiedades/comprar"
    for page in range(2, 6):
        yield f"https://prop.com.uy/propiedades/comprar?page={page}"


def agency_orangehome_mx_list_urls() -> Iterator[str]:
    """Orange Home Guadalajara — home + inmuebles.php."""
    yield "https://www.orangehomeinmobiliaria.com.mx/"
    yield "https://www.orangehomeinmobiliaria.com.mx/inmuebles.php"


def agency_nuevaalianza_py_list_urls() -> Iterator[str]:
    """Nueva Alianza Asunción — listado venta primero."""
    yield "https://inmobiliariana.com.py/"  # listado venta con acentos rompe urllib ascii; home expone /propiedad/{id}
    yield "https://inmobiliariana.com.py/"

def agency_brokers_py_list_urls() -> Iterator[str]:
    """Brokers Paraguay — home expone muchas /propiedad/{id}_slug."""
    yield "https://www.brokers.com.py/"
    yield "https://www.brokers.com.py/propiedades/"
    for page in range(2, 6):
        yield f"https://www.brokers.com.py/page/{page}/"


def agency_canepa_uy_list_urls() -> Iterator[str]:
    """Cánepa UY — listados por tipo en venta."""
    for path in (
        "casas/en-venta/",
        "apartamentos/en-venta/",
        "terrenos/en-venta/",
        "campos/en-venta/",
    ):
        yield f"https://www.canepa.com.uy/{path}"

def agency_gorlero_uy_list_urls() -> Iterator[str]:
    """Gorlero PDE — listados por tipo en venta (mismo patrón Canepa)."""
    for path in (
        "casas/en-venta/",
        "apartamentos/en-venta/",
        "terrenos/en-venta/",
        "campos/en-venta/",
    ):
        yield f"https://www.inmobiliariagorlero.com/{path}"


def agency_dunod_ar_list_urls() -> Iterator[str]:
    """Dunod Rosario — WP inmuebles status=venta + paginación."""
    yield "https://dunod.com.ar/inmuebles/?status%5B%5D=venta"
    for page in range(2, 8):
        yield f"https://dunod.com.ar/inmuebles/page/{page}/?status%5B%5D=venta"


def agency_habitat_ar_list_urls() -> Iterator[str]:
    """Hábitat Rosario — Tokko /p/{id}-slug; listados Venta + Propiedades."""
    yield "https://www.habitatinmobiliariarosario.com/Venta"
    yield "https://www.habitatinmobiliariarosario.com/Propiedades"
    for page in range(2, 6):
        yield f"https://www.habitatinmobiliariarosario.com/Venta?page={page}"


def agency_newport_uy_list_urls() -> Iterator[str]:
    """Newport Montevideo — Tokko /p/{id}-slug; /Venta filtra alquiler."""
    yield "https://www.newportpropiedades.com/Venta"
    yield "https://www.newportpropiedades.com/Buscar"
    for page in range(2, 5):
        yield f"https://www.newportpropiedades.com/Venta?page={page}"


def agency_marcaraices_uy_list_urls() -> Iterator[str]:
    """Marca Raíces UY — listados por tipo en venta (mismo patrón Canepa)."""
    for path in (
        "apartamentos/en-venta/",
        "casas/en-venta/",
        "terrenos/en-venta/",
        "campos/en-venta/",
        "chacras/en-venta/",
        "locales/en-venta/",
        "oficinas/en-venta/",
    ):
        yield f"https://www.marcaraices.com/{path}"
