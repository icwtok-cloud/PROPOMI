"""Tests de la demanda genérica B2B: /demand-requests (create/list/delete) +
matching automático contra alta manual de propiedad (create_property)."""
from sqlalchemy import select, delete
from fastapi.testclient import TestClient

from app.main import (
    app, engine, Session, User, Agency, Property, Role,
    LeadCredit, Subscription, SubscriptionPlan,
    DemandRequest, DemandMatch, Event,
    migrate_agency_monetization, create_token,
)

client = TestClient(app)


def _reset_agency(agency_id, *, plan=None, phone=None):
    phone = phone or f"+54919{abs(hash(agency_id)) % 100000000:08d}"
    with Session(engine) as db:
        db.execute(delete(LeadCredit).where(LeadCredit.agency_id == agency_id))
        db.execute(delete(Subscription).where(Subscription.agency_id == agency_id))
        a = db.get(Agency, agency_id)
        if not a:
            a = Agency(id=agency_id, name=f"Agencia {agency_id}", city="BA", phone=phone, claimed=True)
            db.add(a)
        else:
            a.phone = phone
        a.verification_status = "VERIFIED"
        a.verified = True
        a.free_leads_remaining = 10
        a.subscription_tier = plan
        db.commit()
    migrate_agency_monetization()
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        uid = f"u-dr-{agency_id}"
        agent = db.get(User, uid)
        if not agent:
            existing = db.scalar(select(User).where(User.phone == a.phone))
            if existing:
                existing.agency_id = agency_id
                existing.role = Role.AGENTE.value
                db.commit()
                return create_token(existing)
            agent = User(id=uid, phone=a.phone, role=Role.AGENTE.value, agency_id=agency_id)
            db.add(agent)
            db.commit()
        else:
            agent.agency_id = agency_id
            db.commit()
        return create_token(agent)


def _clear_demand(agency_id):
    with Session(engine) as db:
        db.execute(delete(DemandRequest).where(DemandRequest.agency_id == agency_id))
        db.commit()


def test_create_demand_request_blocked_for_plan_30():
    token = _reset_agency("dr-a30", plan=SubscriptionPlan.PLAN_30.value)
    r = client.post(
        "/demand-requests",
        json={"zone": "Palermo", "property_type": "Departamento", "rooms_min": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403, r.text


def test_create_list_delete_demand_request_plan_50():
    _clear_demand("dr-a50")
    token = _reset_agency("dr-a50", plan=SubscriptionPlan.PLAN_50.value)
    r = client.post(
        "/demand-requests",
        json={"zone": "Caballito", "property_type": "Departamento", "rooms_min": 2, "price_max": 150000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["zone"] == "Caballito"
    assert body["active"] is True
    did = body["id"]

    r2 = client.get("/demand-requests", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert any(d["id"] == did for d in r2.json())

    r3 = client.delete(f"/demand-requests/{did}", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200, r3.text
    assert r3.json()["active"] is False


def test_create_demand_request_plan_99_allowed():
    _clear_demand("dr-a99")
    token = _reset_agency("dr-a99", plan=SubscriptionPlan.PLAN_99.value)
    r = client.post(
        "/demand-requests",
        json={"zone": "Nueva Cordoba", "property_type": "Departamento"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text


def test_delete_demand_request_requires_ownership():
    _clear_demand("dr-owner1")
    _clear_demand("dr-owner2")
    token1 = _reset_agency("dr-owner1", plan=SubscriptionPlan.PLAN_50.value)
    token2 = _reset_agency("dr-owner2", plan=SubscriptionPlan.PLAN_50.value)
    r = client.post(
        "/demand-requests", json={"zone": "Belgrano", "property_type": "Departamento"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    did = r.json()["id"]
    r2 = client.delete(f"/demand-requests/{did}", headers={"Authorization": f"Bearer {token2}"})
    assert r2.status_code == 404


def test_manual_property_creation_matches_demand_and_creates_event():
    """Agencia B (PLAN_50) busca 2 amb en Recoleta hasta 200k. Agencia A carga
    una propiedad manual que matchea -> debe crear DemandMatch + Event
    demand_match para la agencia B, sin exponer datos de comprador (no hay)."""
    _clear_demand("dr-buyer-agency")
    token_seller = _reset_agency("dr-seller-agency", plan=SubscriptionPlan.PLAN_50.value)
    token_buyer_agency = _reset_agency("dr-buyer-agency", plan=SubscriptionPlan.PLAN_50.value)

    r = client.post(
        "/demand-requests",
        json={"zone": "Recoleta", "property_type": "Departamento", "rooms_min": 2, "price_max": 200000},
        headers={"Authorization": f"Bearer {token_buyer_agency}"},
    )
    demand_id = r.json()["id"]

    with Session(engine) as db:
        before = db.scalar(select(Event.id).where(Event.name == "demand_match", Event.agency_id == "dr-buyer-agency"))

    rp = client.post(
        "/properties",
        json={
            "title": "Depto 2 amb Recoleta", "type": "Departamento", "operation": "Venta",
            "price": 180000, "currency": "USD", "zone": "Recoleta", "city": "CABA",
            "surface": 55, "rooms": 2, "bedrooms": 1, "bathrooms": 1,
        },
        headers={"Authorization": f"Bearer {token_seller}"},
    )
    assert rp.status_code == 201, rp.text
    prop_id = rp.json()["id"]

    with Session(engine) as db:
        match = db.scalar(
            select(DemandMatch).where(
                DemandMatch.demand_request_id == demand_id,
                DemandMatch.property_id == prop_id,
            )
        )
        assert match is not None
        ev = db.scalar(select(Event).where(Event.name == "demand_match", Event.property_id == prop_id))
        assert ev is not None
        assert ev.agency_id == "dr-buyer-agency"
        assert ev.context.get("channel") == "B2B"


def test_property_does_not_match_own_agency_demand():
    """La agencia nunca recibe demand_match de su propia publicación."""
    _clear_demand("dr-self-agency")
    token = _reset_agency("dr-self-agency", plan=SubscriptionPlan.PLAN_50.value)
    client.post(
        "/demand-requests",
        json={"zone": "Villa Urquiza", "property_type": "Departamento"},
        headers={"Authorization": f"Bearer {token}"},
    )
    rp = client.post(
        "/properties",
        json={
            "title": "Depto Villa Urquiza", "type": "Departamento", "operation": "Venta",
            "price": 100000, "currency": "USD", "zone": "Villa Urquiza", "city": "CABA",
            "surface": 40, "rooms": 1, "bedrooms": 1, "bathrooms": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    prop_id = rp.json()["id"]
    with Session(engine) as db:
        match = db.scalar(select(DemandMatch).where(DemandMatch.property_id == prop_id))
        assert match is None
