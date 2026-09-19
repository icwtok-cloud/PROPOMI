"""Auth admin sobre main.py actual (rate limit + AdminAuditLog + dual auth)."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/padmin_re.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")
os.environ.setdefault("ADMIN_USERNAME", "owner")
os.environ.setdefault("ADMIN_PASSWORD", "secret123")
os.environ.setdefault("ADMIN_PHONE", "+5491155559999")

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app, engine, AdminUser, ensure_admin_seed

client = TestClient(app)


def test_seed_admin_user():
    ensure_admin_seed()
    with Session(engine) as db:
        u = db.scalars(select(AdminUser).where(AdminUser.username == "owner")).first()
        assert u is not None
        assert bcrypt.checkpw(b"secret123", u.password_hash.encode())


def test_admin_login_wrong_password():
    ensure_admin_seed()
    r = client.post("/admin/auth/login", json={"username": "owner", "password": "wrongpass"})
    assert r.status_code == 401


def test_admin_login_and_otp_flow():
    ensure_admin_seed()
    r = client.post("/admin/auth/login", json={"username": "owner", "password": "secret123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("otpRequired") is True
    code = body.get("dev_code")
    assert code and len(code) == 6
    v = client.post("/admin/auth/verify-otp", json={"username": "owner", "code": code})
    assert v.status_code == 200, v.text
    token = v.json()["token"]
    assert v.json()["user"]["role"] == "ADMIN"
    me = client.get("/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"
    p = client.get("/admin/agencies/pending", headers={"Authorization": f"Bearer {token}"})
    assert p.status_code == 200
    assert isinstance(p.json(), list)
    # shape: phone / instagram / websiteLink / verificationPriority
    for row in p.json():
        assert "phone" in row
        assert "websiteLink" in row
        assert "verificationPriority" in row


def test_admin_key_still_works_for_pending():
    r = client.get("/admin/agencies/pending", headers={"X-Admin-Key": "test-admin-key"})
    assert r.status_code == 200


def test_no_public_admin_registration():
    r = client.post("/admin/auth/register", json={"username": "hacker", "password": "x"})
    assert r.status_code in (404, 405, 401, 403)
