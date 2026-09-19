"""Tests de antigüedad de propiedades (hidden_at / expire_stale_properties)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi_expiry.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from app.main import (
    app, engine, Base, Session, Property, expire_stale_properties, ADMIN_KEY,
)

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)

ADMIN_HEADERS = {"X-Admin-Key": ADMIN_KEY}


def _make_prop(pid: str, days_ago_detected: int, origin_iso: str | None = None, **kwargs):
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        p = Property(
            id=pid,
            title=f"Prop {pid}",
            type="Departamento",
            operation="Venta",
            price=100000,
            currency="USD",
            zone="Caballito",
            city="Buenos Aires",
            surface=50,
            rooms=2,
            freshness="test",
            source="test",
            source_url=f"https://example.com/{pid}",
            image="#",
            images=["#"],
            description="test",
            detected_at=now - timedelta(days=days_ago_detected),
            last_seen_at=now,
            origin_published_at=origin_iso,
            hidden_at=None,
            **kwargs,
        )
        db.add(p)
        db.commit()
        return p.id


def test_expire_hides_100_day_old():
    _make_prop("exp-old", days_ago_detected=100)
    with Session(engine) as db:
        report = expire_stale_properties(db)
    assert report["hidden"] >= 1
    with Session(engine) as db:
        p = db.get(Property, "exp-old")
        assert p.hidden_at is not None


def test_expire_keeps_30_day_old():
    _make_prop("exp-fresh", days_ago_detected=30)
    with Session(engine) as db:
        expire_stale_properties(db)
    with Session(engine) as db:
        p = db.get(Property, "exp-fresh")
        assert p.hidden_at is None


def test_origin_published_at_overrides_detected_at():
    """origin_published_at ISO viejo manda aunque detected_at sea reciente."""
    old_iso = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    _make_prop("exp-origin", days_ago_detected=5, origin_iso=old_iso)
    with Session(engine) as db:
        report = expire_stale_properties(db)
    assert report["hidden"] >= 1
    with Session(engine) as db:
        p = db.get(Property, "exp-origin")
        assert p.hidden_at is not None


def test_get_properties_hides_hidden():
    _make_prop("exp-vis", days_ago_detected=10)
    with Session(engine) as db:
        p = db.get(Property, "exp-vis")
        p.hidden_at = datetime.now(timezone.utc)
        db.commit()
    r = client.get("/properties")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert "exp-vis" not in ids


def test_get_properties_include_hidden_requires_admin():
    _make_prop("exp-admin", days_ago_detected=10)
    with Session(engine) as db:
        p = db.get(Property, "exp-admin")
        p.hidden_at = datetime.now(timezone.utc)
        db.commit()
    # sin admin key no aparece
    r = client.get("/properties?include_hidden=true")
    ids = [x["id"] for x in r.json()]
    assert "exp-admin" not in ids
    # con admin key sí
    r = client.get("/properties?include_hidden=true", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert "exp-admin" in ids


def test_admin_expire_endpoint():
    _make_prop("exp-api", days_ago_detected=120)
    r = client.post("/admin/properties/expire-stale", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "hidden" in body
    assert body["hidden"] >= 1


def test_expire_hides_65_day_old():
    """Con MAX_AGE_DAYS=60, 65 días debe ocultarse (con 90 no lo hacía)."""
    _make_prop("exp-65", days_ago_detected=65)
    with Session(engine) as db:
        report = expire_stale_properties(db)
    assert report["max_age_days"] == 60
    with Session(engine) as db:
        p = db.get(Property, "exp-65")
        assert p.hidden_at is not None
