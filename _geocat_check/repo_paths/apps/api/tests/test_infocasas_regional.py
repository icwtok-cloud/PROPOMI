"""Parsers InfoCasas PY/UY — fixture real __NEXT_DATA__."""
from pathlib import Path

from app.crawler.parsers.infocasas import parse_detail_py, parse_detail_uy
from app.crawler.links import extract_detail_urls

FIX = Path(__file__).parent / "fixtures"


def test_parse_infocasas_py_detail():
    html = (FIX / "infocasas_py_detail.html").read_text(encoding="utf-8", errors="ignore")
    raw = parse_detail_py(
        html,
        "https://www.infocasas.com.py/usd-635000-residencia/194264112",
    )
    assert raw is not None
    assert raw.source == "infocasas_py"
    assert raw.title
    assert raw.price and raw.price >= 1000
    assert raw.images


def test_parse_infocasas_uy_detail():
    html = (FIX / "infocasas_uy_detail.html").read_text(encoding="utf-8", errors="ignore")
    raw = parse_detail_uy(
        html,
        "https://www.infocasas.com.uy/venta-de-casa/194024495",
    )
    assert raw is not None
    assert raw.source == "infocasas_uy"
    assert raw.title
    assert raw.price is None or raw.price >= 0


def test_extract_infocasas_links_from_next_data():
    # minimal blob with a detail url
    html = '''<script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"x":"https://www.infocasas.com.py/foo-bar/194264112"}}}
    </script>'''
    urls = extract_detail_urls("infocasas_py", html, "https://www.infocasas.com.py", limit=10)
    assert any("194264112" in u for u in urls)
