"""Parser MendozaProp contra fixture HTML real (__NEXT_DATA__)."""
from pathlib import Path
from app.crawler.parsers.mendozaprop import parse_detail
from app.crawler.links import extract_detail_urls

FIXTURE = Path(__file__).parent / "fixtures" / "mendozaprop_detail.html"


def test_mendozaprop_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    url = "https://www.mendozaprop.com/venta-apartamento-3-habitaciones-drozd-carina-silvana/6763207"
    raw = parse_detail(html, url)
    assert raw is not None
    assert raw.price and raw.price >= 50000
    assert raw.title
    assert (raw.rooms or raw.bedrooms or 0) >= 1
    assert raw.images and len(raw.images) >= 1
    desc = raw.description or ""
    assert "wa.me" not in desc.lower()
    # strip_contact_leaks ya corrió (precio con teléfono en texto queda sanitizado)
    assert raw.operation == "Venta"


def test_mendozaprop_sitemap_links_only_venta():
    xml = """<?xml version="1.0"?>
    <urlset>
      <loc>https://www.mendozaprop.com/venta-casa-test/123</loc>
      <loc>https://www.mendozaprop.com/alquiler-depto-test/456</loc>
      <loc>https://www.mendozaprop.com/propiedades</loc>
    </urlset>
    """
    urls = extract_detail_urls("mendozaprop", xml, "https://www.mendozaprop.com", limit=20)
    assert any("/venta-" in u for u in urls)
    assert not any("/alquiler-" in u for u in urls)
