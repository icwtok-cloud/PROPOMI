"""Sugerencias agente→agente: otra agencia, hidden_at, rate, sin PII, engage→Event."""
from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_psuggest2.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin")
os.environ["RATE_SUGGESTIONS_PER_AGENCY_DAILY"] = "3"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import (
    app, Session, User, Agency, Property, Offer, Role, Event, create_token,
    PropertySuggestion, RATE_SUGGESTIONS_PER_AGENCY_DAILY, _rate,
)

client = TestClient(app)


def _seed(with_offer=True, hidden_target=False):
    from app.main import engine
    _rate._hits.clear()
    with Session(engine) as db:
        for aid, phone in [("sg-a1", "+5491110000001"), ("sg-a2", "+5491110000002")]:
            a = db.get(Agency, aid)
            if not a:
                db.add(Agency(
                    id=aid, name=f"Ag {aid}", city="BA", phone=phone,
                    claimed=True, verification_status="VERIFIED", verified=True,
                ))
        if not db.get(User, "sg-agent"):
            db.add(User(id="sg-agent", phone="+5491110000001", role=Role.AGENTE.value, agency_id="sg-a1"))
        if not db.get(User, "sg-buyer"):
            db.add(User(
                id="sg-buyer", phone="+5491110000099", role=Role.COMPRADOR.value,
                phone_verified_at=datetime.now(timezone.utc),
            ))
        p1 = db.get(Property, "sg-p1")
        if not p1:
            db.add(Property(
                id="sg-p1", title="Prop A1", price=100000, zone="Palermo", city="BA",
                surface=40, rooms=2, freshness="hoy", source="test", image="#",
                description="x", agency_id="sg-a1",
            ))
        p2 = db.get(Property, "sg-p2")
        if not p2:
            p2 = Property(
                id="sg-p2", title="Prop A2", price=110000, zone="Palermo", city="BA",
                surface=45, rooms=2, freshness="hoy", source="test", image="#",
                description="x", agency_id="sg-a2",
            )
            db.add(p2)
        p2.hidden_at = datetime.now(timezone.utc) if hidden_target else None
        o = db.get(Offer, "sg-o1")
        if with_offer:
            if not o:
                db.add(Offer(
                    id="sg-o1", user_id="sg-buyer", property_id="sg-p1", amount=90000,
                    currency="USD", payment_form="contado", buyer_name="Comprador Secreto",
                    buyer_phone_raw="+5491110000099", buyer_phone_normalized="+5491110000099",
                    buyer_email="secreto@example.com", status="SENT",
                ))
        elif o:
            db.delete(o)
        db.commit()
    from app.main import engine as eng
    with Session(eng) as db:
        agent = db.get(User, "sg-agent")
        buyer = db.get(User, "sg-buyer")
        return create_token(agent), create_token(buyer)


def _assert_no_buyer_pii(obj):
    blob = str(obj).lower()
    assert "buyer_name" not in blob
    assert "buyer_phone" not in blob
    assert "buyer_email" not in blob
    assert "secreto@example.com" not in blob
    assert "comprador secreto" not in blob


def test_suggest_ok_with_active_offer():
    agent_t, buyer_t = _seed(with_offer=True, hidden_target=False)
    r = client.post(
        "/properties/sg-p1/suggest",
        json={"suggested_property_id": "sg-p2"},
        headers={"Authorization": f"Bearer {agent_t}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"].startswith("psg-")
    assert body["status"] == "SENT"
    _assert_no_buyer_pii(body)

    listed = client.get("/buyers/me/suggestions", headers={"Authorization": f"Bearer {buyer_t}"})
    assert listed.status_code == 200
    _assert_no_buyer_pii(listed.json())
    assert any(x["id"] == body["id"] for x in listed.json()["suggestions"])


def test_suggest_400_without_offer():
    agent_t, _ = _seed(with_offer=False, hidden_target=False)
    r = client.post(
        "/properties/sg-p1/suggest",
        json={"suggested_property_id": "sg-p2"},
        headers={"Authorization": f"Bearer {agent_t}"},
    )
    assert r.status_code == 400
    assert "comprador" in r.json()["detail"].lower()


def test_suggest_400_same_agency():
    agent_t, _ = _seed(with_offer=True, hidden_target=False)
    r = client.post(
        "/properties/sg-p1/suggest",
        json={"suggested_property_id": "sg-p1"},
        headers={"Authorization": f"Bearer {agent_t}"},
    )
    assert r.status_code == 400


def test_suggest_404_hidden_target():
    agent_t, _ = _seed(with_offer=True, hidden_target=True)
    r = client.post(
        "/properties/sg-p1/suggest",
        json={"suggested_property_id": "sg-p2"},
        headers={"Authorization": f"Bearer {agent_t}"},
    )
    assert r.status_code == 404


def test_suggest_rate_limit_429():
    agent_t, _ = _seed(with_offer=True, hidden_target=False)
    # crear props target extra de otra agencia para no chocar con unique lógica
    from app.main import engine
    with Session(engine) as db:
        for i in range(5):
            pid = f"sg-px{i}"
            if not db.get(Property, pid):
                db.add(Property(
                    id=pid, title=f"Extra {i}", price=100000 + i, zone="Palermo", city="BA",
                    surface=40, rooms=2, freshness="hoy", source="test", image="#",
                    description="x", agency_id="sg-a2",
                ))
        db.commit()
    codes = []
    for i in range(RATE_SUGGESTIONS_PER_AGENCY_DAILY + 2):
        r = client.post(
            "/properties/sg-p1/suggest",
            json={"suggested_property_id": f"sg-px{i % 5}"},
            headers={"Authorization": f"Bearer {agent_t}"},
        )
        codes.append(r.status_code)
    assert 429 in codes, codes


def test_engage_marks_engaged_and_event_for_target_agency():
    agent_t, buyer_t = _seed(with_offer=True, hidden_target=False)
    r = client.post(
        "/properties/sg-p1/suggest",
        json={"suggested_property_id": "sg-p2"},
        headers={"Authorization": f"Bearer {agent_t}"},
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    eng = client.post(f"/property-suggestions/{sid}/engage", headers={"Authorization": f"Bearer {buyer_t}"})
    assert eng.status_code == 200
    assert eng.json()["status"] == "ENGAGED"
    _assert_no_buyer_pii(eng.json())

    from app.main import engine
    with Session(engine) as db:
        sug = db.get(PropertySuggestion, sid)
        assert sug is not None and sug.status == "ENGAGED" and sug.engaged_at is not None
        ev = db.scalars(
            select(Event).where(Event.name == "suggestion_engaged", Event.agency_id == "sg-a2")
        ).first()
        assert ev is not None
        assert ev.property_id == "sg-p2"
        assert (ev.context or {}).get("suggestion_id") == sid
