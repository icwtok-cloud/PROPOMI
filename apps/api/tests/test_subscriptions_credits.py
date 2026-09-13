"""Tests subscriptions + lead_credits + consumo reveal + POST subscription."""
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.main import (
    app, engine, Base, Session, User, Agency, Property, Offer, Role,
    LeadCredit, Subscription, SubscriptionPlan,
    get_available_credit, migrate_agency_monetization, create_token,
)

client = TestClient(app)


def _reset_agency(agency_id, *, verified=True, free=10, plan=None, used=0, quota=None, phone=None):
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
        a.verification_status = "VERIFIED" if verified else "PENDING"
        a.verified = verified
        a.free_leads_remaining = free
        a.subscription_tier = plan
        a.plan_lead_quota = quota
        a.leads_used_current_period = used
        db.commit()
    migrate_agency_monetization()
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        uid = f"u-sub-{agency_id}"
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


def _seed_offer(agency_id, offer_id, prop_id):
    with Session(engine) as db:
        if not db.get(Property, prop_id):
            db.add(Property(
                id=prop_id, title="Depto test", zone="Palermo", city="BA",
                operation="venta", type="departamento", price=100000, currency="USD",
                surface=50, rooms=2, bedrooms=1, bathrooms=1,
                freshness="nuevo", source="test", source_url="#",
                image="", description="test", agency_id=agency_id,
            ))
        o = db.get(Offer, offer_id)
        if o:
            o.contact_revealed = False
            o.contact_revealed_at = None
            o.property_id = prop_id
        else:
            db.add(Offer(
                id=offer_id, user_id="u-buyer-sub", property_id=prop_id,
                amount=90000, currency="USD", payment_form="contado",
                buyer_name="Ana Test", buyer_phone_raw="+5491199990000",
                buyer_phone_normalized="+5491199990000", buyer_email="ana@test.com",
                status="SENT", contact_revealed=False,
            ))
        db.commit()


def test_get_available_credit_combines_tables():
    _reset_agency("sub-a1", free=5, plan=SubscriptionPlan.PLAN_30.value, used=10, quota=30)
    with Session(engine) as db:
        assert get_available_credit(db, "sub-a1") == 25


def test_reveal_consumes_lead_credits_first():
    token = _reset_agency("sub-a1", free=2, plan=SubscriptionPlan.PLAN_30.value, used=0, quota=30)
    _seed_offer("sub-a1", "sub-o1", "sub-p1")
    r1 = client.post("/offers/sub-o1/reveal", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["method"] == "free_credit"
    with Session(engine) as db:
        lc = db.scalar(select(LeadCredit).where(LeadCredit.agency_id == "sub-a1"))
        assert lc.consumido == 1
        assert get_available_credit(db, "sub-a1") == 31


def test_reveal_falls_to_subscription_after_free_exhausted():
    token = _reset_agency("sub-a1", free=1, plan=SubscriptionPlan.PLAN_30.value, used=0, quota=30)
    _seed_offer("sub-a1", "sub-o2", "sub-p2")
    r1 = client.post("/offers/sub-o2/reveal", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200
    assert r1.json()["method"] == "free_credit"
    with Session(engine) as db:
        if not db.get(Offer, "sub-o3"):
            db.add(Offer(
                id="sub-o3", user_id="u-buyer-sub", property_id="sub-p2",
                amount=91000, currency="USD", payment_form="contado",
                buyer_name="Bob", buyer_phone_raw="+5491188880000",
                buyer_phone_normalized="+5491188880000", status="SENT",
            ))
            db.commit()
    r2 = client.post("/offers/sub-o3/reveal", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["method"] == "subscription_quota"
    with Session(engine) as db:
        sub = db.scalar(select(Subscription).where(Subscription.agency_id == "sub-a1"))
        assert sub.consumido_ciclo == 1


def test_reveal_falls_to_pay_when_both_zero():
    token = _reset_agency("sub-a1", free=0, plan=None, used=0, quota=None)
    _seed_offer("sub-a1", "sub-o4", "sub-p4")
    r = client.post("/offers/sub-o4/reveal", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 402, r.text


def test_migration_preserves_agency_columns():
    with Session(engine) as db:
        db.execute(delete(LeadCredit).where(LeadCredit.agency_id == "mig1"))
        db.execute(delete(Subscription).where(Subscription.agency_id == "mig1"))
        a = db.get(Agency, "mig1")
        if not a:
            a = Agency(
                id="mig1", name="Mig", city="BA", phone="+5491100001111",
                claimed=True, verification_status="VERIFIED", verified=True,
                free_leads_remaining=7, subscription_tier="PLAN_50",
                plan_lead_quota=60, leads_used_current_period=3,
            )
            db.add(a)
        else:
            a.free_leads_remaining = 7
            a.subscription_tier = "PLAN_50"
            a.plan_lead_quota = 60
            a.leads_used_current_period = 3
        db.commit()
    migrate_agency_monetization()
    with Session(engine) as db:
        lc = db.scalar(select(LeadCredit).where(LeadCredit.agency_id == "mig1"))
        assert lc is not None and lc.cupo == 7 and lc.consumido == 0
        sub = db.scalar(select(Subscription).where(Subscription.agency_id == "mig1"))
        assert sub is not None and sub.plan == "PLAN_50" and sub.cupo_ciclo == 60 and sub.consumido_ciclo == 3
        a = db.get(Agency, "mig1")
        assert a.free_leads_remaining == 7 and a.subscription_tier == "PLAN_50"


def test_post_subscription_blocked_if_not_verified():
    token = _reset_agency("a_nv", verified=False, free=0, phone="+5491100998877")
    r = client.post("/agencies/a_nv/subscription", json={"plan": "PLAN_30"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_post_subscription_sets_plan_and_resets_consumido():
    token = _reset_agency("sub-a1", verified=True, free=0, plan=SubscriptionPlan.PLAN_30.value, used=5, quota=30)
    r = client.post("/agencies/sub-a1/subscription", json={"plan": "PLAN_50"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] == "PLAN_50" and body["cupoCiclo"] == 60 and body["consumidoCiclo"] == 0
    with Session(engine) as db:
        a = db.get(Agency, "sub-a1")
        assert a.subscription_tier == "PLAN_50" and a.leads_used_current_period == 0 and a.plan_lead_quota == 60
