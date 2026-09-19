"""priority_score y orden default de GET /properties."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_priority.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app, engine, Base, Session, Property
from app.crawler.normalize import compute_priority_score

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)


def test_high_rotation_scores_above_low():
    now = datetime.now(timezone.utc)
    high = compute_priority_score({
        "origin_published_at": (now - timedelta(days=3)).isoformat(),
        "price": 80000,
        "rooms": 2,
        "surface": 55,
        "images": ["a", "b", "c", "d", "e"],
    }, zone_median_price=100000)
    low = compute_priority_score({
        "origin_published_at": (now - timedelta(days=80)).isoformat(),
        "price": 250000,
        "rooms": 1,
        "surface": 25,
        "images": ["a"],
    }, zone_median_price=100000)
    assert high > low
    assert high >= 50
    assert low < 40


def test_get_properties_orders_by_priority():
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        for pid, score in (("hi-prio", 90.0), ("lo-prio", 10.0)):
            db.add(Property(
                id=pid, title=f"T {pid}", price=100000, zone="Caballito", city="BA",
                surface=50, rooms=2, freshness="t", source="test",
                source_url=f"https://ex/{pid}", image="#", images=["#"],
                description="t", detected_at=now, last_seen_at=now,
                priority_score=score, hidden_at=None,
            ))
        db.commit()
    r = client.get("/properties")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json() if x["id"] in ("hi-prio", "lo-prio")]
    assert ids.index("hi-prio") < ids.index("lo-prio")
