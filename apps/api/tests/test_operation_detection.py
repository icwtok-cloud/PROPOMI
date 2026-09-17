"""Tests de detección de operation (Venta vs Alquiler) y gate del runner."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.crawler.base import detect_operation_from_signals
from app.crawler.parsers.argenprop import parse_detail as parse_argenprop
from app.crawler.parsers.bienesonline import parse_detail as parse_bienesonline
from app.crawler.parsers.cordobaprop import parse_detail as parse_cordobaprop
from app.crawler.parsers.inmoclick import parse_detail as parse_inmoclick
from app.crawler.parsers.inmoup import parse_detail as parse_inmoup
from app.crawler.parsers.mercado_unico import parse_detail as parse_mercado_unico
from app.crawler.parsers.mercadolibre import parse_detail as parse_mercadolibre
from app.crawler.parsers.zonaprop import parse_detail as parse_zonaprop

FIX = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Detector unitario
# ---------------------------------------------------------------------------


def test_detect_from_url_alquiler():
    assert detect_operation_from_signals(url="https://x.com/alquiler-casa-3amb") == "Alquiler"
    assert detect_operation_from_signals(url="https://x.com/propiedades/en-alquiler/123") == "Alquiler"
    assert detect_operation_from_signals(url="https://x.com/?operaciones=2") == "Alquiler"


def test_detect_from_url_venta():
    assert detect_operation_from_signals(url="https://x.com/venta-duplex") == "Venta"
    assert detect_operation_from_signals(url="https://x.com/propiedades/en-venta/99") == "Venta"
    assert detect_operation_from_signals(url="https://x.com/?operaciones=1") == "Venta"


def test_detect_alquiler_priority_over_venta_in_text():
    assert detect_operation_from_signals(title="Venta y Alquiler disponible") == "Alquiler"


def test_detect_from_embedded_dict():
    assert (
        detect_operation_from_signals(embedded={"operacion": "Alquiler"}) == "Alquiler"
    )
    assert detect_operation_from_signals(embedded={"operation_type": "Venta"}) == "Venta"


def test_detect_from_json_ld_business_function():
    html = '''<script type="application/ld+json">
    {"@type":"RealEstateListing","businessFunction":"http://purl.org/goodrelations/v1#LeaseOut"}
    </script>'''
    assert detect_operation_from_signals(html=html) == "Alquiler"


def test_detect_from_breadcrumb_ml():
    html = (FIX / "mercadolibre_alquiler.html").read_text(encoding="utf-8")
    assert detect_operation_from_signals(
        url="https://departamento.mercadolibre.com.ar/MLA-999-_JM",
        html=html,
    ) == "Alquiler"


def test_detect_default_venta_with_no_signal():
    op = detect_operation_from_signals(url="https://example.com/propiedad/123", title="Depto 2 amb")
    assert op == "Venta"


# ---------------------------------------------------------------------------
# Parsers con fixtures Alquiler
# ---------------------------------------------------------------------------


def test_bienesonline_alquiler_fixture():
    html = (FIX / "bienesonline_alquiler.html").read_text(encoding="utf-8")
    raw = parse_bienesonline(html, "https://bienesonline.ai/es/argentina/x/propiedad/1-alquiler")
    assert raw is not None
    assert raw.operation == "Alquiler"


def test_cordobaprop_alquiler_fixture():
    html = (FIX / "cordobaprop_alquiler.html").read_text(encoding="utf-8")
    raw = parse_cordobaprop(html, "https://cordobaprop.com/propiedad/1-alquiler-casa")
    assert raw is not None
    assert raw.operation == "Alquiler"


def test_mercado_unico_alquiler_fixture():
    html = (FIX / "mercado_unico_alquiler.html").read_text(encoding="utf-8")
    raw = parse_mercado_unico(html, "https://mercado-unico.com/propiedades/abc123")
    assert raw is not None
    assert raw.operation == "Alquiler"


def test_inmoup_alquiler_fixture():
    html = (FIX / "inmoup_alquiler.html").read_text(encoding="utf-8")
    raw = parse_inmoup(
        html, "https://www.inmoup.com.ar/departamentos-en-alquiler-en-mendoza/123"
    )
    assert raw is not None
    assert raw.operation == "Alquiler"


def test_inmoclick_alquiler_fixture():
    html = (FIX / "inmoclick_alquiler.html").read_text(encoding="utf-8")
    raw = parse_inmoclick(html, "https://www.inmoclick.com.ar/propiedad/1-alquiler")
    assert raw is not None
    assert raw.operation == "Alquiler"


def test_mercadolibre_alquiler_fixture():
    html = (FIX / "mercadolibre_alquiler.html").read_text(encoding="utf-8")
    raw = parse_mercadolibre(
        html,
        "https://departamento.mercadolibre.com.ar/MLA-999-departamento-en-alquiler-_JM",
    )
    assert raw is not None
    assert raw.operation == "Alquiler"


# ---------------------------------------------------------------------------
# Runner gate (mock sin sqlalchemy real)
# ---------------------------------------------------------------------------


def _make_existing(**kwargs):
    defaults = dict(
        title="x",
        price=100,
        description="",
        type="Departamento",
        operation="Venta",
        currency="USD",
        zone="",
        city="",
        country="AR",
        province="",
        surface=None,
        rooms=None,
        bedrooms=None,
        bathrooms=None,
        images=[],
        image=None,
        last_seen_at=None,
        hidden_at=None,
        priority_score=None,
        origin_published_at=None,
        source_url="https://example.com/p/1",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_runner_hides_existing_when_now_alquiler():
    existing = _make_existing(operation="Venta", hidden_at=None)
    db = MagicMock()
    db.scalar.return_value = existing

    payload = {
        "title": "Depto",
        "price": 100,
        "description": "",
        "type": "Departamento",
        "operation": "Alquiler",
        "currency": "USD",
        "zone": "",
        "city": "",
        "images": [],
        "source_url": "https://example.com/p/1",
    }

    # Stubs para imports lazy dentro de upsert_payload
    fake_prop = type("Property", (), {"source_url": SimpleNamespace()})
    with patch.dict(
        "sys.modules",
        {
            "sqlalchemy": MagicMock(),
            "app.main": MagicMock(
                Property=fake_prop,
                MAX_PROPERTY_IMAGES=5,
                match_demand_requests_for_property=MagicMock(),
            ),
        },
    ):
        # sqlalchemy.select needs .where chain
        import sys

        sa = sys.modules["sqlalchemy"]
        sel = MagicMock()
        sel.where.return_value = sel
        sa.select = MagicMock(return_value=sel)

        from app.crawler.runner import upsert_payload

        status = upsert_payload(db, payload, "testsrc")

    assert status == "updated"
    assert existing.operation == "Alquiler"
    assert existing.hidden_at is not None


def test_runner_shows_existing_when_still_venta():
    existing = _make_existing(operation="Venta", hidden_at="old")
    db = MagicMock()
    db.scalar.return_value = existing

    payload = {
        "title": "Depto",
        "price": 100,
        "description": "",
        "type": "Departamento",
        "operation": "Venta",
        "currency": "USD",
        "zone": "",
        "city": "",
        "images": [],
        "source_url": "https://example.com/p/1",
    }

    fake_prop = type("Property", (), {"source_url": SimpleNamespace()})
    with patch.dict(
        "sys.modules",
        {
            "sqlalchemy": MagicMock(),
            "app.main": MagicMock(
                Property=fake_prop,
                MAX_PROPERTY_IMAGES=5,
                match_demand_requests_for_property=MagicMock(),
            ),
        },
    ):
        import sys

        sa = sys.modules["sqlalchemy"]
        sel = MagicMock()
        sel.where.return_value = sel
        sa.select = MagicMock(return_value=sel)

        from app.crawler.runner import upsert_payload

        status = upsert_payload(db, payload, "testsrc")

    assert status == "updated"
    assert existing.operation == "Venta"
    assert existing.hidden_at is None
