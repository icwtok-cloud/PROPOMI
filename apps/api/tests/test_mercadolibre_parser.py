"""Parser MercadoLibre JSON-LD contra fixture real."""
from pathlib import Path
from app.crawler.parsers.mercadolibre import parse_detail
from app.crawler.links import extract_detail_urls

FIXTURE = Path(__file__).parent / "fixtures" / "mercadolibre_detail.html"


def test_mercadolibre_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    url = "https://inmueble.mercadolibre.com.ar/MLA-2050801037"
    raw = parse_detail(html, url)
    assert raw is not None
    assert raw.price and raw.price >= 10000
    assert raw.title
    assert raw.images
    assert "wa.me" not in (raw.description or "").lower()


def test_mercadolibre_link_extraction():
    html = '''
    <a href="/MLA-2050801037">x</a>
    <a href="https://casa.mercadolibre.com.ar/MLA-2076280135-foo">y</a>
    '''
    urls = extract_detail_urls("mercadolibre", html, "https://inmuebles.mercadolibre.com.ar", limit=10)
    assert any("MLA-2050801037" in u for u in urls)
