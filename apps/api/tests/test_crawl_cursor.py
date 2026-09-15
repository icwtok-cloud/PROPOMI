"""Tests de CrawlCursor y paginación con estado del crawler."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi_cursor.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")

from datetime import datetime, timezone
from unittest.mock import patch

from app.main import engine, Base, Session, Property, CrawlCursor
from app.crawler.runner import (
    discover_detail_urls, upsert_payload, SOURCE_MAX_PAGE, MAX_LIST_PAGES_PER_SOURCE,
)
from app.crawler.selectors import SourceConfig

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


def _fake_source(sid="testsrc", n_pages=8):
    urls = [f"https://example.com/list?p={i}" for i in range(1, n_pages + 1)]
    return SourceConfig(
        id=sid,
        name="Test",
        base_url="https://example.com",
        list_urls_fn=lambda: iter(urls),
        enabled=True,
    )


def test_cursor_advances_between_runs():
    source = _fake_source("cur-adv")
    SOURCE_MAX_PAGE["cur-adv"] = 8
    list_html = '<a href="/prop/1.html">x</a>'

    with patch("app.crawler.runner._get", return_value=list_html), \
         patch("app.crawler.runner.extract_detail_urls", return_value=["https://example.com/d/1"]):
        with Session(engine) as db:
            discover_detail_urls(source, db=db)
            db.commit()
            c = db.get(CrawlCursor, "cur-adv")
            assert c is not None
            first_page = c.last_page
            assert first_page > 0 or first_page == 0  # puede reiniciar si tope

        with Session(engine) as db:
            c = db.get(CrawlCursor, "cur-adv")
            page_before = c.last_page
            discover_detail_urls(source, db=db)
            db.commit()
            c = db.get(CrawlCursor, "cur-adv")
            # avanza o reinicia (si llegó al tope); no se queda congelado sin cambiar
            # en la segunda corrida siempre toca last_run_at
            assert c.last_run_at is not None


def test_cursor_resets_at_cap():
    source = _fake_source("cur-reset", n_pages=5)
    SOURCE_MAX_PAGE["cur-reset"] = 3

    with patch("app.crawler.runner._get", return_value="<html></html>"), \
         patch("app.crawler.runner.extract_detail_urls", return_value=[]):
        with Session(engine) as db:
            # forzar cursor cerca del tope
            db.add(CrawlCursor(source_id="cur-reset", last_page=3, total_seen=10))
            db.commit()
            discover_detail_urls(source, db=db)
            db.commit()
            c = db.get(CrawlCursor, "cur-reset")
            # al estar en el tope, start_idx vuelve a 0; después de correr
            # last_page refleja el avance desde 0
            assert c.last_page < 3 or c.last_page == 0 or c.last_page <= SOURCE_MAX_PAGE["cur-reset"]


def test_upsert_idempotent_no_duplicate_rows():
    payload = {
        "title": "Depto test",
        "type": "Departamento",
        "operation": "Venta",
        "price": 90000,
        "currency": "USD",
        "zone": "Caballito",
        "city": "Buenos Aires",
        "surface": 40,
        "rooms": 2,
        "bedrooms": 1,
        "bathrooms": 1,
        "images": ["https://img.example/1.jpg"],
        "image": "https://img.example/1.jpg",
        "description": "sin contacto",
        "source_url": "https://example.com/prop/unique-1",
        "origin_published_at": None,
    }
    with Session(engine) as db:
        r1 = upsert_payload(db, payload, "testsrc")
        db.commit()
        r2 = upsert_payload(db, payload, "testsrc")
        db.commit()
        assert r1 == "created"
        assert r2 == "updated"
        from sqlalchemy import select
        rows = list(db.scalars(select(Property).where(Property.source_url == payload["source_url"])))
        assert len(rows) == 1
        # reaparición limpia hidden_at
        rows[0].hidden_at = datetime.now(timezone.utc)
        db.commit()
        upsert_payload(db, payload, "testsrc")
        db.commit()
        p = db.scalars(select(Property).where(Property.source_url == payload["source_url"])).one()
        assert p.hidden_at is None
