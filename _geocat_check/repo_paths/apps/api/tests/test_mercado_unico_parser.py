"""Parser Mercado Único contra fixture HTML real (NUXT + og)."""
from pathlib import Path
from app.crawler.parsers.mercado_unico import parse_detail
from app.crawler.links import extract_detail_urls

FIXTURE = Path(__file__).parent / "fixtures" / "mercado_unico_detail.html"


def test_mercado_unico_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    url = "https://www.mercado-unico.com/propiedades/6aa96dfcc31603466d91df66"
    raw = parse_detail(html, url)
    assert raw is not None
    assert raw.title
    assert "JULIO" in raw.title.upper() or (raw.address and "JULIO" in raw.address.upper())
    assert raw.images  # al menos og:image
    desc = raw.description or ""
    assert "wa.me" not in desc.lower()
    assert "+54 9" not in desc
    # precio puede ser null en algunos avisos del portal; no exigimos >0
    assert raw.operation == "Venta"


def test_mercado_unico_link_extraction():
    html = '''
    <a href="/propiedades/6aa96dfcc31603466d91df66">x</a>
    <a href="/propiedades/abc">bad</a>
    <a href="/propiedades/aaaaaaaaaaaaaaaaaaaaaaaa">ok</a>
    '''
    urls = extract_detail_urls("mercado_unico", html, "https://www.mercado-unico.com", limit=10)
    assert any("6aa96dfcc31603466d91df66" in u for u in urls)
    assert all("/propiedades/" in u and len(u.rstrip("/").split("/")[-1]) == 24 for u in urls)
