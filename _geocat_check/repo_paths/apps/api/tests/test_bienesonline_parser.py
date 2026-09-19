"""Parser BienesOnline — fixture real JSON-LD."""
from pathlib import Path

from app.crawler.parsers.bienesonline import parse_detail
from app.crawler.links import extract_detail_urls

FIX = Path(__file__).parent / "fixtures"


def test_parse_bienesonline_detail():
    html = (FIX / "bienesonline_detail.html").read_text(encoding="utf-8", errors="ignore")
    raw = parse_detail(
        html,
        "https://bienesonline.ai/es/argentina/la-punta/propiedad/127983-vendo-terreno",
    )
    assert raw is not None
    assert raw.source == "bienesonline"
    assert "terreno" in raw.title.lower() or raw.title
    assert raw.price == 20000
    assert raw.currency == "USD"
    assert raw.images


def test_extract_bienesonline_links():
    html = '''
    <a href="https://bienesonline.ai/es/argentina/la-punta/propiedad/127983-vendo-terreno">x</a>
    <a href="/es/argentina/cordoba/propiedad/999001-casa">y</a>
    '''
    urls = extract_detail_urls("bienesonline", html, "https://bienesonline.ai", limit=10)
    assert len(urls) >= 2
    assert any("127983" in u for u in urls)
