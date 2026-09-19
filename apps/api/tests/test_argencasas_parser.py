"""Argencasas + DepartamentosEnPozo + Bullano parsers (fixtures reales)."""
from pathlib import Path

from app.crawler.links import extract_detail_urls
from app.crawler.parsers import argencasas, bullano, departamentosenpozo

FIX = Path(__file__).parent / "fixtures"


def test_argencasas_detail_fixture():
    html = (FIX / "argencasas_detail.html").read_text(encoding="utf-8", errors="replace")
    url = "https://www.argencasas.com/propiedad-casa-venta-quilmes-oeste-381-655"
    listing = argencasas.parse_detail(html, url)
    assert listing is not None
    assert "Quilmes" in listing.title or "quilmes" in listing.title.lower()
    assert listing.source == "argencasas"
    assert listing.property_type in ("Casa", "Departamento", "PH", "Local", "Terreno", "Campo")


def test_argencasas_list_extract():
    html = (FIX / "argencasas_list.html").read_text(encoding="utf-8", errors="replace")
    urls = extract_detail_urls("argencasas", html, "https://www.argencasas.com", limit=50)
    assert len(urls) >= 10
    assert any("/propiedad-" in u for u in urls)


def test_departamentosenpozo_detail_fixture():
    html = (FIX / "departamentosenpozo_detail.html").read_text(encoding="utf-8", errors="replace")
    url = "https://departamentosenpozo.com.ar/desarrollos-inmobiliarios/arcadia-art-residence-coghlan/"
    listing = departamentosenpozo.parse_detail(html, url)
    assert listing is not None
    assert listing.property_type == "En Pozo"
    assert listing.extras.get("under_construction") is True
    assert listing.external_id == "arcadia-art-residence-coghlan"


def test_bullano_detail_fixture():
    html = (FIX / "bullano_detail.html").read_text(encoding="utf-8", errors="replace")
    url = "https://www.bullano.com.ar/campos/ficha/guerrero-406-18116.html"
    listing = bullano.parse_detail(html, url)
    assert listing is not None
    assert listing.property_type in ("Campo", "Chacra")
    assert listing.external_id == "18116"
