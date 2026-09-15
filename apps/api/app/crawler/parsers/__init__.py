from . import (
    argenprop,
    cordobaprop,
    inmoup,
    inmoclick,
    mercadolibre,
    mercado_unico,
    mendozaprop,
    properati,
    zonaprop,
)

PARSERS = {
    "mendozaprop": mendozaprop.parse_detail,
    "mercado_unico": mercado_unico.parse_detail,
    "cordobaprop": cordobaprop.parse_detail,
    "zonaprop": zonaprop.parse_detail,
    "argenprop": argenprop.parse_detail,
    "mercadolibre": mercadolibre.parse_detail,
    "properati": properati.parse_detail,
    "inmoup": inmoup.parse_detail,
    "inmoclick": inmoclick.parse_detail,
}


def parse_by_source(source: str, html: str, url: str):
    fn = PARSERS.get(source)
    if not fn:
        raise KeyError(f"Parser desconocido: {source}")
    return fn(html, url)
