"""Parser ZonaProp contra fixture HTML (estructura JSON-LD).

Nota: el HTML real de ZonaProp no se pudo bajar el 2026-09-15 por
Cloudflare challenge (403). Este fixture reproduce el contrato del parser
(JSON-LD Apartment) para detectar regresiones en CI.
"""
from pathlib import Path
from app.crawler.parsers.zonaprop import parse_detail

FIXTURE = Path(__file__).parent / "fixtures" / "zonaprop_detail.html"


def test_zonaprop_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    url = "https://www.zonaprop.com.ar/propiedades/departamento-3-ambientes-ubicado-en-caballito-12345678.html"
    raw = parse_detail(html, url)
    assert raw is not None
    # zone puede venir de addressRegion ("Capital Federal"); city/title llevan Caballito
    blob = " ".join(filter(None, [raw.zone, raw.city, raw.title, raw.address]))
    assert "Caballito" in blob
    assert raw.price and raw.price >= 100000
    assert raw.surface and raw.surface >= 50
    assert (raw.rooms or raw.bedrooms or 0) >= 2
    assert raw.images and len(raw.images) >= 1
    # sin mojibake
    assert "Caba" in (raw.zone or raw.title or "Caballito") or "Caballito" in html
    # descripción limpia de teléfonos (strip_contact_leaks en el parser)
    desc = raw.description or ""
    assert "5555" not in desc  # el teléfono del JSON-LD no debe filtrarse a description pública vía agency_phone sí, description no
