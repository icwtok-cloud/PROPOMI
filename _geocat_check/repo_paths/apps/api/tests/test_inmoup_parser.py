"""Parser InmoUp contra fixture HTML real (JSON-LD schema.org)."""
from pathlib import Path
from app.crawler.parsers.inmoup import parse_detail

FIXTURE = Path(__file__).parent / "fixtures" / "inmoup_detail.html"


def test_inmoup_parser_fixture():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    url = "https://inmoup.com.ar/10752-nicolas/inmuebles/3/ficha/departamentos-en-venta-en-chile-160-lujan-de-cuyo-mendoza"
    raw = parse_detail(html, url)
    assert raw is not None
    blob = " ".join(filter(None, [raw.zone, raw.city, raw.title, raw.address]))
    assert any(x in blob for x in ("Mendoza", "Luján", "Lujan", "Cuyo"))
    assert raw.price and raw.price >= 50000
    assert raw.images and len(raw.images) >= 1
    desc = raw.description or ""
    # strip_contact_leaks: no teléfonos típicos en description
    assert "+54" not in desc
    assert "wa.me" not in desc.lower()
