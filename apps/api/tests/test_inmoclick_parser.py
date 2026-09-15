"""Parser InmoClick og+HTML contra fixture real."""
from pathlib import Path
from app.crawler.parsers.inmoclick import parse_detail
from app.crawler.links import extract_detail_urls

FIXTURE = Path(__file__).parent / "fixtures" / "inmoclick_detail.html"


def test_inmoclick_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    url = "https://www.inmoclick.com.ar/307502-cimientos-negocios-inmobiliarios/inmuebles/15/ficha/duplex-en-venta-en-iguazu-2620"
    raw = parse_detail(html, url)
    assert raw is not None
    assert raw.title
    assert "wa.me" not in (raw.description or "").lower()
    assert raw.external_id == "15"


def test_inmoclick_link_extraction():
    html = '''
    <a href="/307502-cimientos/inmuebles/15/ficha/duplex-en-venta">x</a>
    <a href="/foo/inmuebles/99/ficha/casa-en-venta-en-barrio">y</a>
    '''
    urls = extract_detail_urls("inmoclick", html, "https://www.inmoclick.com.ar", limit=10)
    assert len(urls) >= 2
    assert all("/ficha/" in u for u in urls)
