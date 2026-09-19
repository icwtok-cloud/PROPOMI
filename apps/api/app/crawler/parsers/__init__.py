from . import (
    argenprop,
    argencasas,
    bienesonline,
    bullano,
    cordobaprop,
    departamentosenpozo,
    infocasas,
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
    "mercadolibre_mx": mercadolibre.parse_detail,
    "properati": properati.parse_detail,
    "inmoup": inmoup.parse_detail,
    "inmoclick": inmoclick.parse_detail,
    "infocasas_py": infocasas.parse_detail_py,
    "infocasas_uy": infocasas.parse_detail_uy,
    "bienesonline": bienesonline.parse_detail,
    "argencasas": argencasas.parse_detail,
    "departamentosenpozo": departamentosenpozo.parse_detail,
    "bullano": bullano.parse_detail,
}


def parse_by_source(source: str, html: str, url: str):
    fn = PARSERS.get(source)
    if not fn:
        raise KeyError(f"Parser desconocido: {source}")
    return fn(html, url)
