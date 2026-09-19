from . import (
    agency_nuevaalianza_py,
    agency_orangehome_mx,
    agency_prop_uy,
    tokko_agency,
    argenprop,
    argencasas,
    bienesonline,
    bullano,
    cordobaprop,
    departamentosenpozo,
    grupoedisur,
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
    "grupoedisur": grupoedisur.parse_detail,
    "agency_paganini_ar": tokko_agency.parse_detail_paganini,
    "agency_prey_ar": tokko_agency.parse_detail_prey,
    "agency_prop_uy": agency_prop_uy.parse_detail,
    "agency_orangehome_mx": agency_orangehome_mx.parse_detail,
    "agency_nuevaalianza_py": agency_nuevaalianza_py.parse_detail,
}


def parse_by_source(source: str, html: str, url: str):
    fn = PARSERS.get(source)
    if not fn:
        raise KeyError(f"Parser desconocido: {source}")
    return fn(html, url)
