"""T8.7 — carrera multi-agente por listing_group.

Cubre:
- Agente fuera del grupo → 403
- Dentro de ventana con suscriptores → solo la sub más antigua puede revelar
- Agente sin prioridad (sub más nueva) → 403 antes de ventana
- Pasada la ventana → cualquiera del grupo puede revelar
- Segundo reveal del mismo offer → 409 (no doble cobro / no fuga de contacto)

Run: pytest -q apps/api/tests/test_t87_listing_group_reveal.py
"""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi_t87.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")

from fastapi.testclient import TestClient
from app.main import (
    app, engine, Base, Session, User, Agency, Property, Offer, Role, create_token,
    LISTING_GROUP_REVEAL_WINDOW_WITH_SUB_HOURS,
)

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)

GROUP_ID = "lg-test-t87"
NOW = datetime.now(timezone.utc)


def _reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _seed_group(*, old_sub_start, new_sub_start, offer_created_at):
    """Dos agencias VERIFIED en el mismo listing_group, una oferta sobre p-a."""
    with Session(engine) as db:
        a_old = Agency(
            id="ag-old",
            name="Agencia Antigua",
            city="BA",
            phone="+5491110000001",
            claimed=True,
            verified=True,
            verification_status="VERIFIED",
            subscription_tier="STARTER",
            subscription_started_at=old_sub_start,
            plan_lead_quota=50,
            leads_used_current_period=0,
            free_leads_remaining=0,
        )
        a_new = Agency(
            id="ag-new",
            name="Agencia Nueva",
            city="BA",
            phone="+5491110000002",
            claimed=True,
            verified=True,
            verification_status="VERIFIED",
            subscription_tier="STARTER",
            subscription_started_at=new_sub_start,
            plan_lead_quota=50,
            leads_used_current_period=0,
            free_leads_remaining=0,
        )
        outsider = Agency(
            id="ag-out",
            name="Fuera del grupo",
            city="BA",
            phone="+5491110000003",
            claimed=True,
            verified=True,
            verification_status="VERIFIED",
            free_leads_remaining=5,
        )
        db.add_all([a_old, a_new, outsider])
        db.add(Property(
            id="p-a", title="Depto A", price=100000, zone="Palermo", city="BA",
            surface=40, rooms=2, freshness="hoy", source="test", image="#",
            description="test", agency_id="ag-old", listing_group_id=GROUP_ID,
        ))
        db.add(Property(
            id="p-b", title="Depto B", price=105000, zone="Palermo", city="BA",
            surface=42, rooms=2, freshness="hoy", source="test", image="#",
            description="test", agency_id="ag-new", listing_group_id=GROUP_ID,
        ))
        db.add(Property(
            id="p-out", title="Otra", price=90000, zone="Belgrano", city="BA",
            surface=35, rooms=2, freshness="hoy", source="test", image="#",
            description="test", agency_id="ag-out",
        ))
        buyer = User(id="u-buyer", phone="guest-buyer-t87", role=Role.COMPRADOR.value)
        u_old = User(id="u-old", phone="+5491110000001", role=Role.AGENTE.value, agency_id="ag-old")
        u_new = User(id="u-new", phone="+5491110000002", role=Role.AGENTE.value, agency_id="ag-new")
        u_out = User(id="u-out", phone="+5491110000003", role=Role.AGENTE.value, agency_id="ag-out")
        db.add_all([buyer, u_old, u_new, u_out])
        offer = Offer(
            id="off-t87",
            user_id="u-buyer",
            property_id="p-a",
            amount=95000,
            currency="USD",
            payment_form="CASH",
            status="SENT",
            buyer_name="Comprador Test",
            buyer_phone_raw="11 2222-3333",
            buyer_phone_normalized="+5491122223333",
            contact_revealed=False,
            created_at=offer_created_at,
        )
        db.add(offer)
        db.commit()
        return create_token(u_old), create_token(u_new), create_token(u_out)


def test_outsider_cannot_reveal():
    _reset()
    _, _, tok_out = _seed_group(
        old_sub_start=NOW - timedelta(days=365),
        new_sub_start=NOW - timedelta(days=30),
        offer_created_at=NOW - timedelta(hours=1),
    )
    r = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_out}"})
    assert r.status_code == 403


def test_newer_subscription_blocked_inside_window():
    _reset()
    _, tok_new, _ = _seed_group(
        old_sub_start=NOW - timedelta(days=365),
        new_sub_start=NOW - timedelta(days=30),
        offer_created_at=NOW - timedelta(hours=1),  # dentro de 24h
    )
    r = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_new}"})
    assert r.status_code == 403
    assert "prioridad" in r.json()["detail"].lower() or "suscripci" in r.json()["detail"].lower()


def test_oldest_subscription_can_reveal_inside_window():
    _reset()
    tok_old, _, _ = _seed_group(
        old_sub_start=NOW - timedelta(days=365),
        new_sub_start=NOW - timedelta(days=30),
        offer_created_at=NOW - timedelta(hours=1),
    )
    r = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_old}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("buyer_phone")
    assert body.get("buyer_name") == "Comprador Test"


def test_after_window_newer_can_reveal_if_still_open():
    _reset()
    hours = LISTING_GROUP_REVEAL_WINDOW_WITH_SUB_HOURS + 1
    _, tok_new, _ = _seed_group(
        old_sub_start=NOW - timedelta(days=365),
        new_sub_start=NOW - timedelta(days=30),
        offer_created_at=NOW - timedelta(hours=hours),
    )
    r = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_new}"})
    assert r.status_code == 200, r.text


def test_second_agent_gets_409_after_first_reveal():
    _reset()
    tok_old, tok_new, _ = _seed_group(
        old_sub_start=NOW - timedelta(days=365),
        new_sub_start=NOW - timedelta(days=30),
        offer_created_at=NOW - timedelta(hours=1),
    )
    r1 = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_old}"})
    assert r1.status_code == 200, r1.text
    r2 = client.post("/offers/off-t87/reveal", headers={"Authorization": f"Bearer {tok_new}"})
    assert r2.status_code == 409
    # No debe filtrar el teléfono al segundo
    detail = r2.json().get("detail", "")
    assert "11 2222" not in str(detail)
    assert "buyer_phone" not in r2.json()
