"""Security regression tests for Propomi API.

Run in the project environment with: pytest -q
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")

from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime, timezone
from app.main import app, engine, Base, Session, User, Agency, AgencyPhone, Role, create_token

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

client = TestClient(app)


def seed_users():
    with Session(engine) as db:
        agency = db.get(Agency, "a1")
        if not agency:
            agency = Agency(
                id="a1", name="Agencia 1", city="BA", phone="+5491155550101", claimed=True,
                verification_status="VERIFIED", verified=True,
            )
            db.add(agency)
        else:
            agency.verification_status = "VERIFIED"
            agency.verified = True
        buyer = db.get(User, "u1")
        now = datetime.now(timezone.utc)
        if not buyer:
            buyer = User(
                id="u1", phone="guest-buyer", role=Role.COMPRADOR.value,
                phone_verified_at=now, google_verified_at=now,
            )
            db.add(buyer)
        else:
            buyer.phone_verified_at = buyer.phone_verified_at or now
            buyer.google_verified_at = buyer.google_verified_at or now
        agent = db.get(User, "u2")
        if not agent:
            agent = User(id="u2", phone="+5491155550101", role=Role.AGENTE.value, agency_id="a1")
            db.add(agent)
        db.commit()
        return create_token(buyer), create_token(agent)


def seed_property(agency_id="a1"):
    from app.main import Property
    with Session(engine) as db:
        if not db.get(Property, "p1"):
            db.add(Property(id="p1", title="Depto test", price=100000, zone="Palermo", city="BA",
                             surface=40, rooms=2, freshness="hoy", source="test", image="#",
                             description="test", agency_id=agency_id))
            db.commit()


def test_sensitive_endpoints_require_auth():
    assert client.get("/offers").status_code == 401
    assert client.get("/events/funnel").status_code == 401
    assert client.get("/analytics/summary").status_code == 401


def test_guest_session_is_buyer_only():
    r = client.post("/auth/guest")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "COMPRADOR"
    assert r.json()["user"]["agency_id"] is None


def test_contact_requests_is_agent_only_not_buyer():
    # El canal B2B (contact-requests) es exclusivamente agente<->agencia.
    # Un comprador nunca debe poder llamarlo — antes filtraba el teléfono
    # de la agencia directamente al comprador, dirección incorrecta.
    buyer_token, _ = seed_users()
    headers = {"Authorization": f"Bearer {buyer_token}"}
    r = client.post("/contact-requests", json={"agency_id": "a1", "property_id": "missing"}, headers=headers)
    assert r.status_code == 403


def test_contact_request_unknown_property_returns_404_for_agent():
    _, agent_token = seed_users()
    headers = {"Authorization": f"Bearer {agent_token}"}
    r = client.post("/contact-requests", json={"agency_id": "a1", "property_id": "missing"}, headers=headers)
    assert r.status_code == 404


def test_offer_requires_buyer_name_and_phone():
    buyer_token, _ = seed_users()
    seed_property()
    headers = {"Authorization": f"Bearer {buyer_token}"}
    # Sin buyer_name/buyer_phone, Pydantic debe rechazar con 422.
    r = client.post("/offers", json={"property_id": "p1", "amount": 90000}, headers=headers)
    assert r.status_code == 422


def test_offer_rejects_contact_leak_in_comment():
    buyer_token, _ = seed_users()
    seed_property()
    headers = {"Authorization": f"Bearer {buyer_token}"}
    r = client.post("/offers", json={
        "property_id": "p1", "amount": 90000, "buyer_name": "Juan Pérez",
        "buyer_phone": "+5491122223333", "comment": "Llamame al 11-4444-5555",
    }, headers=headers)
    assert r.status_code == 400


def test_reveal_blocked_without_subscription_or_payment():
    buyer_token, agent_token = seed_users()
    seed_property()
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    r = client.post("/offers", json={
        "property_id": "p1", "amount": 90000, "buyer_name": "Juan Pérez", "buyer_phone": "+5491122223333",
    }, headers=buyer_headers)
    assert r.status_code == 201
    offer_id = r.json()["id"]

    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    reveal = client.post(f"/offers/{offer_id}/reveal", headers=agent_headers)
    # Sin suscripción activa y sin pasarela de pago real integrada (mock
    # siempre deniega), el reveal NUNCA debe entregar el contacto gratis.
    assert reveal.status_code == 402
    assert "buyer_phone" not in reveal.json()

    # Confirmar el pago vía el endpoint mock de desarrollo debe destrabarlo.
    transaction_id = reveal.json()["detail"]["transaction_id"]
    confirm = client.post(f"/payments/{transaction_id}/mock-complete", headers=agent_headers)
    assert confirm.status_code == 200
    assert confirm.json()["buyer_phone"] == "+5491122223333"


def test_offers_list_never_exposes_buyer_contact_before_reveal():
    buyer_token, agent_token = seed_users()
    seed_property()
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    client.post("/offers", json={
        "property_id": "p1", "amount": 91000, "buyer_name": "Ana Gómez", "buyer_phone": "+5491199998888",
    }, headers=buyer_headers)

    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    r = client.get("/offers", headers=agent_headers)
    assert r.status_code == 200
    for offer in r.json():
        if not offer["contact_revealed"]:
            assert "buyer_phone" not in offer
            assert "buyer_name" not in offer


def test_agent_can_add_secondary_phone_and_it_becomes_login_capable():
    _, agent_token = seed_users()
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    add = client.post("/agencies/a1/phones", json={"phone": "+54 9 11 4444-5566"}, headers=agent_headers)
    assert add.status_code == 200
    body = add.json()
    assert body["phone"] == "+5491144445566"
    assert body["verified"] is False

    listed = client.get("/agencies/a1/phones", headers=agent_headers)
    assert listed.status_code == 200
    assert listed.json()["primary"] == "+5491155550101"
    assert any(p["phone"] == "+5491144445566" for p in listed.json()["extras"])

    # El nuevo teléfono ya sirve para pedir/verificar OTP y loguearse como esa agencia.
    req = client.post("/auth/otp/request", json={"phone": "+5491144445566"})
    assert req.status_code == 200
    code = req.json()["dev_code"]
    verify = client.post("/auth/otp/verify", json={"phone": "+5491144445566", "code": code})
    assert verify.status_code == 200
    assert verify.json()["user"]["agency_id"] == "a1"


def test_cannot_add_phone_already_used_by_another_agency():
    _, agent_token = seed_users()
    with Session(engine) as db:
        if not db.get(Agency, "a2"):
            db.add(Agency(id="a2", name="Agencia 2", city="BA", phone="+5491155559999", claimed=True))
            db.commit()
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    r = client.post("/agencies/a1/phones", json={"phone": "+5491155559999"}, headers=agent_headers)
    assert r.status_code == 409


def test_cannot_add_phone_to_agency_that_is_not_yours():
    _, agent_token = seed_users()
    with Session(engine) as db:
        if not db.get(Agency, "a3"):
            db.add(Agency(id="a3", name="Agencia 3", city="BA", phone="+5491100002222", claimed=True))
            db.commit()
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    r = client.post("/agencies/a3/phones", json={"phone": "+5491100003333"}, headers=agent_headers)
    assert r.status_code == 403


def test_otp_request_vonage_hides_dev_code(monkeypatch):
    """Con OTP_SMS_PROVIDER=vonage la respuesta no incluye dev_code."""
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "OTP_SMS_PROVIDER", "vonage")

    class FakeVonage:
        def send(self, phone, code):
            pass

    monkeypatch.setattr(main_mod, "sms_sender", FakeVonage())
    r = client.post("/auth/otp/request", json={"phone": "+5491155550101"})
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert "dev_code" not in r.json()


def test_otp_request_vonage_failure_returns_502(monkeypatch):
    """Fallo de envío → 502 explícito."""
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "OTP_SMS_PROVIDER", "vonage")

    class FailingVonage:
        def send(self, phone, code):
            raise HTTPException(status_code=502, detail="No se pudo enviar el SMS")

    monkeypatch.setattr(main_mod, "sms_sender", FailingVonage())
    r = client.post("/auth/otp/request", json={"phone": "+5491155550101"})
    assert r.status_code == 502


def test_vonage_send_otp_sms_posts_classic_api(monkeypatch):
    """send_otp_sms llama rest.nexmo.com con api_key, from=Propomi y to sin +."""
    import app.sms_vonage as vonage_mod

    monkeypatch.setattr(vonage_mod, "VONAGE_API_KEY", "test-key")
    monkeypatch.setattr(vonage_mod, "VONAGE_API_SECRET", "test-secret")
    monkeypatch.setattr(vonage_mod, "VONAGE_SMS_FROM", "Propomi")

    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"message-count": "1", "messages": [{"status": "0", "to": "5491155550101"}]}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = dict(data or {})
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(vonage_mod.requests, "post", fake_post)
    body = vonage_mod.send_otp_sms("+5491155550101", "123456")
    assert captured["url"] == "https://rest.nexmo.com/sms/json"
    assert captured["data"]["api_key"] == "test-key"
    assert captured["data"]["api_secret"] == "test-secret"
    assert captured["data"]["from"] == "Propomi"
    assert captured["data"]["to"] == "5491155550101"
    assert "123456" in captured["data"]["text"]
    assert body["messages"][0]["status"] == "0"


def test_vonage_send_otp_sms_raises_on_nonzero_status(monkeypatch):
    import app.sms_vonage as vonage_mod
    from app.sms_vonage import VonageSMSError

    monkeypatch.setattr(vonage_mod, "VONAGE_API_KEY", "k")
    monkeypatch.setattr(vonage_mod, "VONAGE_API_SECRET", "s")

    class FakeResp:
        status_code = 200

        def json(self):
            return {"messages": [{"status": "15", "error-text": "Invalid sender"}]}

    monkeypatch.setattr(vonage_mod.requests, "post", lambda *a, **k: FakeResp())
    try:
        vonage_mod.send_otp_sms("5491155550101", "999999")
        assert False, "expected VonageSMSError"
    except VonageSMSError as e:
        assert "15" in str(e)
