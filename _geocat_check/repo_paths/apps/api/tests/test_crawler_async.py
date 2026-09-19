"""POST /admin/crawler/run responde 202 y expone status sin bloquear."""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_crawl_async.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")

from fastapi.testclient import TestClient

# re-import after env
from app import main as main_mod
from app.main import app, ADMIN_KEY

client = TestClient(app)
HDR = {"X-Admin-Key": ADMIN_KEY}


def test_admin_crawler_run_returns_202_immediately():
    main_mod._CRAWL_RUNS.clear()

    def fake_run_crawl(db, source_ids=None, on_progress=None):
        if on_progress:
            on_progress({
                "phase": "source_done",
                "current_source": "cordobaprop",
                "completed_sources": ["cordobaprop"],
                "planned_sources": ["cordobaprop"],
                "sources": {"cordobaprop": {"created": 1}},
                "ok": True,
            })
            on_progress({
                "phase": "finished",
                "current_source": None,
                "completed_sources": ["cordobaprop"],
                "planned_sources": ["cordobaprop"],
                "sources": {"cordobaprop": {"created": 1}},
                "ok": True,
            })
        return {"sources": {"cordobaprop": {"created": 1}}, "ok": True, "planned_sources": ["cordobaprop"]}

    with patch("app.crawler.run_crawl", side_effect=fake_run_crawl):
        r = client.post("/admin/crawler/run?source=cordobaprop", headers=HDR)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "accepted"
    assert body["crawl_run_id"].startswith("crun-")
    rid = body["crawl_run_id"]

    # BackgroundTasks runs before TestClient returns from request when using default
    st = client.get(f"/admin/crawler/status/{rid}", headers=HDR)
    assert st.status_code == 200
    data = st.json()
    assert data["crawl_run_id"] == rid
    assert data["status"] in ("queued", "running", "completed", "failed")


def test_admin_crawler_status_latest():
    main_mod._CRAWL_RUNS.clear()
    main_mod._crawl_run_upsert("crun-testlatest", status="completed", sources={"x": {}})
    r = client.get("/admin/crawler/status", headers=HDR)
    assert r.status_code == 200
    assert r.json()["crawl_run_id"] == "crun-testlatest"
