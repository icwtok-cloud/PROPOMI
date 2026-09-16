"""Prioridad de cola de crawleo entre fuentes enabled."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_crawl_prio.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin")

from app.main import Session, engine, CrawlCursor, DemandRequest, Property, Agency
from app.crawler.crawl_queue_priority import compute_source_priority, compute_source_scores
from app.crawler.selectors import SOURCES
from app.crawler import runner as runner_mod


def _enabled_ids() -> list[str]:
    return [sid for sid, s in SOURCES.items() if s.enabled]


def test_never_crawled_source_ranks_first():
    """Fuente sin CrawlCursor (nunca crawleada) queda antes que una reciente."""
    enabled = _enabled_ids()
    assert len(enabled) >= 2
    a, b = enabled[0], enabled[1]
    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        # limpiar cursores de enabled
        for sid in enabled:
            c = db.get(CrawlCursor, sid)
            if c:
                db.delete(c)
        # b se crawleó hace 1 hora
        db.add(CrawlCursor(source_id=b, last_page=1, total_seen=10, last_run_at=now - timedelta(hours=1)))
        # a sin cursor = nunca
        db.commit()
        order = compute_source_priority(db)

    assert order[0] == a
    assert order.index(a) < order.index(b)


def test_demand_boosts_source_with_matching_inventory():
    """DemandRequest en zona X sube la fuente que ya tiene props en X."""
    enabled = _enabled_ids()
    assert len(enabled) >= 2
    src_hot, src_cold = enabled[0], enabled[1]
    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        for sid in enabled:
            c = db.get(CrawlCursor, sid)
            if c:
                db.delete(c)
            # misma antigüedad → desempatan por demanda
            db.add(CrawlCursor(
                source_id=sid, last_page=1, total_seen=5,
                last_run_at=now - timedelta(hours=10),
            ))
        # inventario
        if not db.get(Agency, "prio-ag"):
            db.add(Agency(
                id="prio-ag", name="Prio", city="Córdoba", phone="+5493510009999",
                claimed=True, verification_status="VERIFIED", verified=True,
            ))
        for pid, src, zone in [
            ("prio-p-hot", src_hot, "Nueva Córdoba"),
            ("prio-p-cold", src_cold, "Zona Fría XYZ"),
        ]:
            existing = db.get(Property, pid)
            if existing:
                existing.source = src
                existing.zone = zone
            else:
                db.add(Property(
                    id=pid, title=f"P {pid}", price=100000, zone=zone, city="Córdoba",
                    surface=40, rooms=2, freshness="hoy", source=src, image="#",
                    description="x", agency_id="prio-ag",
                ))
        # demanda en Nueva Córdoba
        for old in db.scalars(
            __import__("sqlalchemy", fromlist=["select"]).select(DemandRequest)
        ).all():
            db.delete(old)
        db.add(DemandRequest(
            id="prio-dr-1",
            agency_id="prio-ag",
            zone="Nueva Córdoba",
            property_type="Departamento",
            rooms_min=2,
            price_max=200000,
            active=True,
            created_at=now,
            expires_at=now + timedelta(days=30),
        ))
        db.commit()
        order = compute_source_priority(db)
        scores = {sid: sc for sid, sc, _ in compute_source_scores(db)}

    assert scores[src_hot] > scores[src_cold], scores
    assert order.index(src_hot) < order.index(src_cold)


def test_run_crawl_without_sources_uses_priority_order():
    enabled = _enabled_ids()
    seen: list[str] = []

    def fake_run_source(db, source):
        seen.append(source.id)
        return {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    with Session(engine) as db:
        for sid in enabled:
            c = db.get(CrawlCursor, sid)
            if c:
                db.delete(c)
        db.commit()
        expected = compute_source_priority(db)

        with patch.object(runner_mod, "run_source", side_effect=fake_run_source):
            runner_mod.run_crawl(db, source_ids=None)

    assert seen == expected


def test_run_crawl_with_explicit_sources_keeps_caller_order():
    enabled = _enabled_ids()
    explicit = list(reversed(enabled))
    seen: list[str] = []

    def fake_run_source(db, source):
        seen.append(source.id)
        return {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    with Session(engine) as db:
        with patch.object(runner_mod, "run_source", side_effect=fake_run_source):
            runner_mod.run_crawl(db, source_ids=explicit)

    assert seen == explicit
