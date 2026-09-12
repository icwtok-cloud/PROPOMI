from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Protocol

import jwt
import phonenumbers
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, create_engine, select, text, inspect, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# --------------------------------------------------------------------------
# Filtro anti-fuga de contacto (ver doc 05 de la especificación de negocio).
# Se aplica a cualquier campo de texto libre que llegue del comprador o del
# agente (ej. comentarios de oferta/contraoferta) ANTES de guardarlo o
# devolverlo — nunca se persiste texto sin sanitizar.
# --------------------------------------------------------------------------
_LEAK_PATTERNS = [
    re.compile(r"(\+?54)?[\s\-\.]?9?[\s\-\.]?\(?\d{2,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}"),  # teléfonos AR con variantes
    re.compile(r"\bwsp\b|\bwhatsapp\b|\bwapp\b", re.IGNORECASE),
    re.compile(r"\b(cel|tel|celular|telefono|teléfono)\s*[:\-]?\s*\d", re.IGNORECASE),
    re.compile(r"@[a-zA-Z0-9_.]{3,}"),  # menciones de usuario de redes sociales
    re.compile(r"https?://|www\.", re.IGNORECASE),  # URLs externas
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # emails sueltos en texto libre
]


def contains_contact_leak(texto: str | None) -> bool:
    if not texto:
        return False
    return any(pattern.search(texto) for pattern in _LEAK_PATTERNS)


def sanitize_free_text(texto: str | None, campo: str = "comentario") -> str | None:
    """Devuelve el texto tal cual si está limpio. Si detecta un posible dato de
    contacto, rechaza con un error claro en vez de guardarlo silenciosamente
    filtrado — coherente con la política definida para el crawler (doc 05):
    bloquear y explicar el motivo, no censurar en silencio."""
    if texto and contains_contact_leak(texto):
        raise HTTPException(
            status_code=400,
            detail=f"El campo '{campo}' no puede contener teléfonos, emails, usuarios de redes sociales ni links. "
                   f"La plataforma protege el contacto de ambas partes hasta que corresponda revelarlo.",
        )
    return texto

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_format(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise HTTPException(status_code=400, detail="Ingresá un email válido.")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./propomi.db")
ENV = os.getenv("ENV", "development").lower()
JWT_SECRET = os.getenv("JWT_SECRET")
if ENV == "production" and not JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be configured in production")
JWT_SECRET = JWT_SECRET or "dev-only-change-me"
JWT_ALGORITHM = "HS256"
OTP_TTL_SECONDS = 5 * 60
OTP_RATE_WINDOW = 10 * 60
OTP_MAX_REQUESTS = 3

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


class Role(str, Enum):
    COMPRADOR = "COMPRADOR"
    AGENTE = "AGENTE"


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(60), default="Departamento")
    operation: Mapped[str] = mapped_column(String(20), default="Venta")
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    zone: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Argentina")
    surface: Mapped[float] = mapped_column(Float)
    rooms: Mapped[int] = mapped_column(Integer)
    bedrooms: Mapped[int] = mapped_column(Integer, default=1)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1)
    parking: Mapped[bool] = mapped_column(Boolean, default=False)
    pool: Mapped[bool] = mapped_column(Boolean, default=False)
    balcony: Mapped[bool] = mapped_column(Boolean, default=False)
    pet_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    credit: Mapped[bool] = mapped_column(Boolean, default=False)
    freshness: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(160))
    source_url: Mapped[str] = mapped_column(String(500), default="#")
    image: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str] = mapped_column(Text)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_phone_raw: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_phone_normalized: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    property_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    city: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)
    # Suscripción — null significa pay-per-lead puro (sin plan activo).
    # plan_lead_quota: None = ilimitado (plan USD 99); un número = tope mensual.
    subscription_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plan_lead_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leads_used_current_period: Mapped[int] = mapped_column(Integer, default=0)
    subscription_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.COMPRADOR.value)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class IntentProfile(Base):
    __tablename__ = "intent_profiles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    level: Mapped[int] = mapped_column(Integer, default=1)
    intent: Mapped[str] = mapped_column(String(40), default="VIEW")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    financing: Mapped[str | None] = mapped_column(String(30), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    decision_maker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    alternatives: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    payment_form: Mapped[str] = mapped_column(String(30))
    capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    # Contacto real del comprador — es lo que efectivamente se "revela" al
    # agente. Nunca se devuelve en ningún endpoint hasta que exista un reveal
    # válido (ver /offers/{id}/reveal).
    buyer_name: Mapped[str] = mapped_column(String(120))
    buyer_phone_raw: Mapped[str] = mapped_column(String(40))
    buyer_phone_normalized: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    buyer_email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_revealed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class RevealMethod(str, Enum):
    SUBSCRIPTION_QUOTA = "SUBSCRIPTION_QUOTA"
    PAY_PER_LEAD = "PAY_PER_LEAD"


class RevealTransaction(Base):
    """Registra cada intento/consumo de reveal de contacto de comprador.
    Es el punto de enganche para una pasarela de pago real (Mercado Pago,
    Stripe, etc.) — ver PaymentGateway más abajo."""
    __tablename__ = "reveal_transactions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(40), index=True)
    agency_id: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(30))
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | COMPLETED | FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentSuppressionList(Base):
    """Lista de baja permanente — un teléfono/email acá nunca vuelve a
    recibir contacto en frío ni ver sus datos reutilizados, aunque el
    crawler lo vuelva a encontrar en otra fuente (ver doc 05)."""
    __tablename__ = "agent_suppression_list"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_e164: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True, unique=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CounterOffer(Base):
    __tablename__ = "counter_offers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ContactRequest(Base):
    __tablename__ = "contact_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(40))
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    requester_role: Mapped[str] = mapped_column(String(20), default=Role.COMPRADOR.value)
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED")
    billable: Mapped[bool] = mapped_column(Boolean, default=True)
    shared_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class OTPCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(30), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# create_all is enough for a fresh database. The small ALTER pass below keeps existing
# local/Render databases compatible with this incremental product stage.
Base.metadata.create_all(engine)


def ensure_schema_columns() -> None:
    required = {
        "properties": {
            "contact_phone_raw": "VARCHAR(80)",
            "contact_phone_normalized": "VARCHAR(30)",
        },
        "agencies": {
            "phone": "VARCHAR(30)",
            "subscription_tier": "VARCHAR(20)",
            "plan_lead_quota": "INTEGER",
            "leads_used_current_period": "INTEGER DEFAULT 0",
            "subscription_started_at": "TIMESTAMP",
            "current_period_start": "TIMESTAMP",
        },
        "contact_requests": {
            "requester_role": "VARCHAR(20) DEFAULT 'COMPRADOR'",
            "billable": "BOOLEAN DEFAULT TRUE",
            "shared_phone": "VARCHAR(30)",
        },
        "otp_codes": {"verify_attempts": "INTEGER DEFAULT 0"},
        "offers": {
            "buyer_name": "VARCHAR(120) DEFAULT ''",
            "buyer_phone_raw": "VARCHAR(40) DEFAULT ''",
            "buyer_phone_normalized": "VARCHAR(30)",
            "buyer_email": "VARCHAR(160)",
            "contact_revealed": "BOOLEAN DEFAULT FALSE",
            "contact_revealed_at": "TIMESTAMP",
        },
    }
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in required.items():
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspect(conn).get_columns(table)}
            for column, ddl in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))




ensure_schema_columns()

app = FastAPI(title="Propomi API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SmsSender(Protocol):
    def send(self, phone: str, code: str) -> None: ...


class MockSmsSender:
    def send(self, phone: str, code: str) -> None:
        if ENV != "production":
            print(f"[PROPOMI OTP MOCK] {phone} -> {code}")


sms_sender: SmsSender = MockSmsSender()
OTP_MAX_VERIFY_ATTEMPTS = 5


class PaymentGateway(Protocol):
    def charge(self, agency_id: str, amount_usd: float, reference: str) -> bool: ...


class MockPaymentGateway:
    """Seam para una pasarela real (Mercado Pago, Stripe, etc.). A propósito
    NUNCA aprueba un cobro por sí sola — devuelve False siempre, para que
    jamás se revele un contacto 'gratis' por accidente mientras no haya una
    integración real. En desarrollo, el pago se completa manualmente vía
    POST /payments/{transaction_id}/mock-complete (bloqueado en producción)."""
    def charge(self, agency_id: str, amount_usd: float, reference: str) -> bool:
        if ENV != "production":
            print(f"[PROPOMI PAYMENT MOCK] Cobro pendiente: agencia={agency_id} monto=USD{amount_usd} ref={reference}")
        return False


payment_gateway: PaymentGateway = MockPaymentGateway()
PAY_PER_LEAD_USD = 5.0


def normalize_phone(raw: str, default_country: str = "AR") -> str | None:
    value = raw.strip()
    if not value:
        return None
    try:
        parsed = phonenumbers.parse(value, default_country)
        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "phone": user.phone,
        "role": user.role,
        "agency_id": user.agency_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_session(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida") from exc


def current_user(session: dict[str, Any] = Depends(current_session)) -> User:
    with Session(engine) as db:
        user = db.get(User, session.get("user_id"))
        if not user or user.phone != session.get("phone") or user.role != session.get("role") or user.agency_id != session.get("agency_id"):
            raise HTTPException(status_code=401, detail="Sesión inválida")
        return user


def require_agent(session: dict[str, Any] = Depends(current_session)) -> dict[str, Any]:
    if session.get("role") != Role.AGENTE.value or not session.get("agency_id"):
        raise HTTPException(status_code=403, detail="Se requiere una sesión de agente")
    return session


DEMO = [
    {"id":"p1","title":"Departamento luminoso 2 ambientes","type":"Departamento","operation":"Venta","price":118000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":45,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":False,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 2 días","source":"Inmobiliaria Norte","source_url":"#","image":"https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=85","description":"Unidad renovada, muy luminosa y con balcón.","agency_id":"a1","contact_phone_raw":"11 5555-0101"},
    {"id":"p2","title":"Departamento moderno con balcón","type":"Departamento","operation":"Venta","price":120000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":43,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":True,"pool":False,"balcony":True,"pet_friendly":False,"credit":True,"freshness":"Actualizada hace 4 días","source":"Red Urbana","source_url":"#","image":"https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1000&q=85","description":"Edificio moderno con cochera y amenities.","agency_id":"a2","contact_phone_raw":"+54 9 11 5555-0202"},
    {"id":"p3","title":"2 ambientes amplio a estrenar","type":"Departamento","operation":"Venta","price":125000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":48,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":True,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 6 días","source":"Habitar","source_url":"#","image":"https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=85","description":"A estrenar, excelente distribución.","agency_id":"a1","contact_phone_raw":"11 5555-0101"},
    {"id":"p4","title":"Departamento 3 ambientes con patio","type":"Departamento","operation":"Venta","price":138000,"currency":"USD","zone":"Villa Crespo","city":"Buenos Aires","surface":62,"rooms":3,"bedrooms":2,"bathrooms":1,"parking":False,"pool":False,"balcony":False,"pet_friendly":True,"credit":True,"freshness":"Actualizada hace 1 día","source":"Urbania","source_url":"#","image":"https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1000&q=85","description":"Patio y ambientes amplios para familia.","agency_id":"a3","contact_phone_raw":"11 5555-0303"},
]


ALLOWED_EVENTS = {
    "property_view", "property_save", "property_compare", "property_question",
    "visit_request", "offer_created", "contact_requested", "contact_shared",
    "counter_offer_created", "negotiation_started", "operation_advanced",
}


class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    property_id: str | None = None
    session_id: str | None = Field(default=None, max_length=80)
    context: dict[str, Any] = Field(default_factory=dict)


class OfferIn(BaseModel):
    property_id: str
    amount: float
    payment_form: str = "MIXED"
    capital: float | None = None
    timeframe: str | None = None
    comment: str | None = Field(default=None, max_length=500)
    # Contacto real — obligatorio: sin esto no hay nada que revelar después.
    buyer_name: str = Field(min_length=2, max_length=120)
    buyer_phone: str = Field(min_length=6, max_length=40)
    buyer_email: str | None = Field(default=None, max_length=160)

    @field_validator("comment")
    @classmethod
    def check_comment_leak(cls, v: str | None) -> str | None:
        return sanitize_free_text(v, campo="comentario")

    @field_validator("buyer_email")
    @classmethod
    def check_email_format(cls, v: str | None) -> str | None:
        return validate_email_format(v)


class CounterIn(BaseModel):
    amount: float
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment")
    @classmethod
    def check_comment_leak(cls, v: str | None) -> str | None:
        return sanitize_free_text(v, campo="comentario")


class ContactIn(BaseModel):
    agency_id: str
    property_id: str


class IntentIn(BaseModel):
    property_id: str
    intent: str
    level: int
    budget: float | None = None
    capital: float | None = None
    financing: str | None = None
    timeframe: str | None = None
    decision_maker: str | None = None
    alternatives: bool = False


class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    code: str


class AgencyUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)


def ensure_seed(db: Session) -> None:
    if db.scalar(select(Property.id).limit(1)) is None:
        for row in DEMO:
            row = dict(row)
            row["contact_phone_normalized"] = normalize_phone(row["contact_phone_raw"])
            db.add(Property(**row))
        db.add_all([
            Agency(id="a1", name="Inmobiliaria Norte", city="Buenos Aires", verified=True, claimed=True, phone=normalize_phone("11 5555-0101")),
            Agency(id="a2", name="Red Urbana", city="Buenos Aires", verified=True, claimed=False, phone=normalize_phone("+54 9 11 5555-0202")),
            Agency(id="a3", name="Urbania", city="Buenos Aires", verified=False, claimed=False, phone=normalize_phone("11 5555-0303")),
        ])
        db.commit()
    else:
        rows = db.scalars(select(Property)).all()
        changed = False
        for p in rows:
            if p.contact_phone_raw and not p.contact_phone_normalized:
                p.contact_phone_normalized = normalize_phone(p.contact_phone_raw)
                changed = True
        if changed:
            db.commit()


@app.get("/health")
def health():
    return {"status": "ok", "service": "propomi-api", "version": "1.1.0"}


@app.post("/auth/guest")
def guest_session():
    """Create a non-privileged buyer identity for anonymous marketplace actions."""
    with Session(engine) as db:
        user = User(id=f"u-guest-{uuid.uuid4().hex[:16]}", phone=f"guest-{uuid.uuid4().hex[:20]}", role=Role.COMPRADOR.value)
        db.add(user)
        db.commit()
        return {"token": create_token(user), "user": {"id": user.id, "phone": user.phone, "role": user.role, "agency_id": user.agency_id}}


@app.post("/auth/otp/request")
def request_otp(payload: OTPRequest):
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Ingresá un teléfono válido")
    now_dt = datetime.now(timezone.utc)
    with Session(engine) as db:
        recent_count = db.scalar(select(text("count(*)")).select_from(OTPCode).where(OTPCode.phone == phone, OTPCode.created_at >= now_dt - timedelta(seconds=OTP_RATE_WINDOW))) or 0
        if recent_count >= OTP_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="Alcanzaste el límite de solicitudes. Probá nuevamente más tarde.")
        code = f"{secrets.randbelow(1_000_000):06d}"
        db.query(OTPCode).filter(OTPCode.phone == phone, OTPCode.consumed == False).update({"consumed": True})
        db.add(OTPCode(phone=phone, code_hash=hash_otp(code), expires_at=datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)))
        db.commit()
    sms_sender.send(phone, code)
    response = {"ok": True, "message": "Te enviamos un código de verificación."}
    if ENV != "production":
        response["dev_code"] = code
    return response


@app.post("/auth/otp/verify")
def verify_otp(payload: OTPVerify):
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Teléfono inválido")
    with Session(engine) as db:
        otp = db.scalar(select(OTPCode).where(OTPCode.phone == phone, OTPCode.consumed == False).order_by(OTPCode.created_at.desc()))
        if not otp or otp.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Código incorrecto o vencido")
        if otp.verify_attempts >= OTP_MAX_VERIFY_ATTEMPTS:
            otp.consumed = True
            db.commit()
            raise HTTPException(status_code=429, detail="Demasiados intentos. Solicitá un nuevo código más tarde.")
        if not secrets.compare_digest(otp.code_hash, hash_otp(payload.code)):
            otp.verify_attempts += 1
            if otp.verify_attempts >= OTP_MAX_VERIFY_ATTEMPTS:
                otp.consumed = True
            db.commit()
            raise HTTPException(status_code=400, detail="Código incorrecto o vencido")
        otp.consumed = True
        user = db.scalar(select(User).where(User.phone == phone))
        agency = db.scalar(select(Agency).where(Agency.phone == phone))
        if user is None:
            if not agency:
                raise HTTPException(status_code=403, detail="No encontramos una agencia asociada a este teléfono.")
            user = User(id=f"u-{uuid.uuid4().hex[:12]}", phone=phone, role=Role.AGENTE.value, agency_id=agency.id)
            db.add(user)
            db.flush()
        elif user.role != Role.AGENTE.value:
            if not agency or (user.agency_id and user.agency_id != agency.id):
                raise HTTPException(status_code=403, detail="Este teléfono pertenece a otra cuenta y no puede convertirse en agente desde este acceso.")
            user.role = Role.AGENTE.value
            user.agency_id = agency.id
        elif not user.agency_id:
            if not agency:
                raise HTTPException(status_code=403, detail="La cuenta no tiene una agencia asociada.")
            user.agency_id = agency.id
        if not agency:
            agency = db.get(Agency, user.agency_id)
        if agency:
            agency.claimed = True
        relinked = relink_properties(db, user.agency_id, phone)
        db.commit()
        token = create_token(user)
        return {"token": token, "user": {"id": user.id, "phone": user.phone, "role": user.role, "agency_id": user.agency_id}, "relinked_count": relinked}


def relink_properties(db: Session, agency_id: str, phone: str) -> int:
    rows = db.scalars(select(Property).where(Property.contact_phone_normalized == phone)).all()
    changed = 0
    for p in rows:
        if p.agency_id != agency_id:
            p.agency_id = agency_id
            changed += 1
    return changed


def prop_dict(p: Property) -> dict[str, Any]:
    return {
        "id": p.id, "title": p.title, "type": p.type, "operation": p.operation, "price": p.price, "currency": p.currency,
        "zone": p.zone, "city": p.city, "country": p.country, "surface": p.surface, "rooms": p.rooms, "bedrooms": p.bedrooms,
        "bathrooms": p.bathrooms, "parking": p.parking, "pool": p.pool, "balcony": p.balcony, "petFriendly": p.pet_friendly,
        "credit": p.credit, "freshness": p.freshness, "source": p.source, "sourceUrl": p.source_url, "image": p.image,
        "description": p.description, "agencyId": p.agency_id, "detectedAt": p.detected_at.isoformat(), "lastSeenAt": p.last_seen_at.isoformat(),
    }


@app.get("/properties")
def properties(zone: str | None = None, operation: str | None = None, rooms: int | None = None, max_price: float | None = None, parking: bool | None = None, credit: bool | None = None, agency_id: str | None = None):
    with Session(engine) as db:
        ensure_seed(db)
        stmt = select(Property)
        if zone: stmt = stmt.where(Property.zone == zone)
        if operation: stmt = stmt.where(Property.operation == operation)
        if rooms: stmt = stmt.where(Property.rooms == rooms)
        if max_price: stmt = stmt.where(Property.price <= max_price)
        if parking is not None: stmt = stmt.where(Property.parking == parking)
        if credit is not None: stmt = stmt.where(Property.credit == credit)
        if agency_id: stmt = stmt.where(Property.agency_id == agency_id)
        return [prop_dict(p) for p in db.scalars(stmt).all()]


@app.get("/properties/{property_id}")
def property_detail(property_id: str):
    with Session(engine) as db:
        ensure_seed(db)
        p = db.get(Property, property_id)
        if not p: raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        return prop_dict(p)


@app.post("/events", status_code=201)
def create_event(payload: EventIn, authorization: str | None = Header(default=None)):
    session = None
    if authorization:
        session = current_session(authorization)
    if payload.name not in ALLOWED_EVENTS:
        raise HTTPException(status_code=400, detail="Evento inválido")
    with Session(engine) as db:
        if payload.property_id and not db.get(Property, payload.property_id):
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        event = Event(name=payload.name, property_id=payload.property_id, user_id=session.get("user_id") if session else None, agency_id=session.get("agency_id") if session else None, session_id=payload.session_id, context=payload.context)
        db.add(event)
        db.commit()
        return {"id": event.id, "status": "recorded"}


@app.get("/events/funnel")
def funnel(session: dict[str, Any] = Depends(require_agent)):
    with Session(engine) as db:
        rows = db.execute(select(Event.name, Event.id)).all()
        counts: dict[str, int] = {}
        for name, _ in rows: counts[name] = counts.get(name, 0) + 1
        return counts


@app.post("/intents", status_code=201)
def upsert_intent(payload: IntentIn, session: dict[str, Any] = Depends(current_session)):
    with Session(engine) as db:
        if not db.get(Property, payload.property_id):
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        user_id = session["user_id"]
        stmt = select(IntentProfile).where(IntentProfile.user_id == user_id, IntentProfile.property_id == payload.property_id)
        profile = db.scalar(stmt)
        data = payload.model_dump(exclude={"property_id"})
        if profile:
            for k, v in data.items(): setattr(profile, k, v)
            profile.updated_at = datetime.now(timezone.utc)
        else:
            profile = IntentProfile(id=f"i-{uuid.uuid4().hex[:12]}", user_id=user_id, **payload.model_dump(exclude={"property_id"}))
            db.add(profile)
        db.commit()
        return {"id": profile.id, "status": "saved"}


@app.post("/offers", status_code=201)
def create_offer(payload: OfferIn, session: dict[str, Any] = Depends(current_session)):
    if session.get("role") != Role.COMPRADOR.value:
        raise HTTPException(status_code=403, detail="Solo un comprador puede crear una oferta")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")
    buyer_phone_normalized = normalize_phone(payload.buyer_phone)
    if not buyer_phone_normalized:
        raise HTTPException(status_code=400, detail="Ingresá un teléfono de contacto válido")
    with Session(engine) as db:
        p = db.get(Property, payload.property_id)
        if not p: raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        offer_data = payload.model_dump(exclude={"buyer_phone"})
        offer = Offer(
            id=f"o-{uuid.uuid4().hex[:12]}",
            user_id=session["user_id"],
            buyer_phone_raw=payload.buyer_phone,
            buyer_phone_normalized=buyer_phone_normalized,
            **offer_data,
        )
        db.add(offer)
        db.add(Event(name="offer_created", property_id=p.id, user_id=session["user_id"], agency_id=p.agency_id, context={"amount": payload.amount}))
        db.commit()
        return {"id": offer.id, "status": offer.status}


@app.get("/offers")
def list_offers(status: str | None = None, session: dict[str, Any] = Depends(current_session)):
    with Session(engine) as db:
        stmt = select(Offer)
        if session.get("role") == Role.AGENTE.value:
            stmt = stmt.where(Offer.property_id.in_(select(Property.id).where(Property.agency_id == session["agency_id"])))
        else:
            stmt = stmt.where(Offer.user_id == session["user_id"])
        if status: stmt = stmt.where(Offer.status == status)
        offers = db.scalars(stmt.order_by(Offer.created_at.desc())).all()
        result = []
        for o in offers:
            row = {"id":o.id,"user_id":o.user_id,"property_id":o.property_id,"amount":o.amount,"currency":o.currency,"payment_form":o.payment_form,"capital":o.capital,"timeframe":o.timeframe,"comment":o.comment,"status":o.status,"created_at":o.created_at.isoformat(),"contact_revealed":o.contact_revealed}
            # El contacto del comprador SOLO viaja en la respuesta si ya fue
            # revelado formalmente — nunca antes, aunque sea el propio agente
            # dueño de la propiedad quien esté consultando.
            if o.contact_revealed:
                row["buyer_name"] = o.buyer_name
                row["buyer_phone"] = o.buyer_phone_raw
                row["buyer_email"] = o.buyer_email
            result.append(row)
        return result


@app.post("/offers/{offer_id}/counter", status_code=201)
def counter_offer(offer_id: str, payload: CounterIn, session: dict[str, Any] = Depends(require_agent)):
    with Session(engine) as db:
        offer = db.get(Offer, offer_id)
        if not offer: raise HTTPException(status_code=404, detail="Oferta no encontrada")
        prop = db.get(Property, offer.property_id)
        if not prop or prop.agency_id != session["agency_id"]: raise HTTPException(status_code=403, detail="Oferta fuera de tu agencia")
        offer.status = "COUNTERED"
        counter = CounterOffer(id=f"co-{uuid.uuid4().hex[:12]}", offer_id=offer.id, amount=payload.amount, comment=payload.comment)
        db.add(counter)
        db.add(Event(name="counter_offer_created", property_id=offer.property_id, user_id=offer.user_id, agency_id=prop.agency_id, context={"amount": payload.amount}))
        db.commit()
        return {"id": counter.id, "status": counter.status}


@app.post("/offers/{offer_id}/reveal")
def reveal_contact(offer_id: str, session: dict[str, Any] = Depends(require_agent)):
    """
    Único punto del sistema que puede exponer el nombre/teléfono real del
    comprador al agente. Reemplaza el flujo anterior (que revelaba el
    teléfono de la AGENCIA al comprador — dirección invertida respecto del
    modelo de negocio documentado). Reglas:
      1. La propiedad de la oferta debe pertenecer a la agencia del agente.
      2. Si ya fue revelada antes, se devuelve el contacto sin volver a cobrar.
      3. Si la agencia tiene suscripción con cupo disponible, se consume cupo
         (gratis para el agente, ya pagado por adelantado vía la suscripción).
      4. Si no hay cupo o no hay suscripción, se cobra pay-per-lead vía
         PaymentGateway. Con el gateway mock (sin integrar pasarela real),
         esto siempre devuelve 402 con el transaction_id para completar el
         pago — nunca revela gratis por default.
    """
    with Session(engine) as db:
        offer = db.get(Offer, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta no encontrada")
        prop = db.get(Property, offer.property_id)
        if not prop or prop.agency_id != session["agency_id"]:
            raise HTTPException(status_code=403, detail="Oferta fuera de tu agencia")

        if offer.contact_revealed:
            return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "buyer_email": offer.buyer_email, "already_revealed": True}

        agency = db.get(Agency, session["agency_id"])
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")

        now = datetime.now(timezone.utc)
        has_quota = (
            agency.subscription_tier is not None
            and (agency.plan_lead_quota is None or agency.leads_used_current_period < agency.plan_lead_quota)
        )

        if has_quota:
            agency.leads_used_current_period += 1
            offer.contact_revealed = True
            offer.contact_revealed_at = now
            db.add(RevealTransaction(
                id=f"rt-{uuid.uuid4().hex[:12]}", offer_id=offer.id, agency_id=agency.id,
                method=RevealMethod.SUBSCRIPTION_QUOTA.value, amount_usd=0.0, status="COMPLETED", completed_at=now,
            ))
            db.add(Event(name="contact_revealed", property_id=prop.id, user_id=offer.user_id, agency_id=agency.id, context={"method": "subscription_quota"}))
            db.commit()
            return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "buyer_email": offer.buyer_email, "method": "subscription_quota"}

        # Sin cupo de suscripción: pay-per-lead. Buscar si ya hay una
        # transacción completada pendiente de aplicar (idempotencia básica).
        existing_paid = db.scalar(
            select(RevealTransaction).where(
                RevealTransaction.offer_id == offer.id,
                RevealTransaction.status == "COMPLETED",
            )
        )
        if existing_paid:
            offer.contact_revealed = True
            offer.contact_revealed_at = now
            db.commit()
            return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "buyer_email": offer.buyer_email, "method": "pay_per_lead"}

        transaction_id = f"rt-{uuid.uuid4().hex[:12]}"
        charged = payment_gateway.charge(agency_id=agency.id, amount_usd=PAY_PER_LEAD_USD, reference=transaction_id)
        db.add(RevealTransaction(
            id=transaction_id, offer_id=offer.id, agency_id=agency.id,
            method=RevealMethod.PAY_PER_LEAD.value, amount_usd=PAY_PER_LEAD_USD,
            status="COMPLETED" if charged else "PENDING",
            completed_at=now if charged else None,
        ))
        db.commit()

        if not charged:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": f"Se requiere pago de USD {PAY_PER_LEAD_USD} para revelar este contacto.",
                    "transaction_id": transaction_id,
                },
            )
        offer.contact_revealed = True
        offer.contact_revealed_at = now
        db.commit()
        return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "method": "pay_per_lead"}


if ENV != "production":
    @app.post("/payments/{transaction_id}/mock-complete")
    def mock_complete_payment(transaction_id: str, session: dict[str, Any] = Depends(require_agent)):
        """SOLO disponible fuera de producción — simula la confirmación de una
        pasarela real para poder probar el flujo de reveal de punta a punta
        en desarrollo, sin tarjeta ni integración real todavía."""
        with Session(engine) as db:
            txn = db.get(RevealTransaction, transaction_id)
            if not txn or txn.agency_id != session["agency_id"]:
                raise HTTPException(status_code=404, detail="Transacción no encontrada")
            txn.status = "COMPLETED"
            txn.completed_at = datetime.now(timezone.utc)
            offer = db.get(Offer, txn.offer_id)
            if offer:
                offer.contact_revealed = True
                offer.contact_revealed_at = txn.completed_at
            db.commit()
            return {"status": "COMPLETED", "buyer_name": offer.buyer_name if offer else None, "buyer_phone": offer.buyer_phone_raw if offer else None, "buyer_email": offer.buyer_email if offer else None}
def offer_action(offer_id: str, action: str, session: dict[str, Any] = Depends(require_agent)):
    if action not in {"accept", "reject", "negotiate"}: raise HTTPException(status_code=400, detail="Acción inválida")
    with Session(engine) as db:
        offer = db.get(Offer, offer_id)
        if not offer: raise HTTPException(status_code=404, detail="Oferta no encontrada")
        prop = db.get(Property, offer.property_id)
        if not prop or prop.agency_id != session["agency_id"]: raise HTTPException(status_code=403, detail="Oferta fuera de tu agencia")
        status = {"accept":"ACCEPTED","reject":"REJECTED","negotiate":"NEGOTIATION"}[action]
        offer.status = status
        if action == "negotiate":
            db.add(Event(name="negotiation_started", property_id=offer.property_id, user_id=offer.user_id, agency_id=prop.agency_id))
        db.commit()
        return {"status": status}


@app.post("/contact-requests", status_code=201)
def contact_request(payload: ContactIn, session: dict[str, Any] = Depends(require_agent)):
    """
    Canal B2B (agente <-> agencia), gratuito e inmediato — ver doc 03.
    El comprador NUNCA obtiene el contacto de la agencia por acá: su único
    canal para recibir contacto es que un agente pague/consuma cupo para
    revelar SU oferta (ver /offers/{id}/reveal). Antes, este endpoint le
    devolvía el teléfono de la agencia directamente al comprador, que es la
    dirección incorrecta respecto del modelo de negocio documentado.
    """
    with Session(engine) as db:
        agency = db.get(Agency, payload.agency_id)
        prop = db.get(Property, payload.property_id)
        if not agency or not prop: raise HTTPException(status_code=404, detail="Agencia o propiedad no encontrada")
        if prop.agency_id != agency.id: raise HTTPException(status_code=400, detail="La propiedad no pertenece a la agencia indicada")

        if agency.phone:
            suppressed = db.scalar(
                select(AgentSuppressionList).where(AgentSuppressionList.phone_e164 == agency.phone)
            )
            if suppressed:
                raise HTTPException(status_code=403, detail="Esta agencia solicitó no recibir más contactos en la plataforma.")

        req_id = f"cr-{uuid.uuid4().hex[:12]}"
        request = ContactRequest(
            id=req_id, agency_id=agency.id, user_id=session["user_id"], property_id=prop.id,
            requester_role=Role.AGENTE.value, status="SHARED", billable=False, shared_phone=agency.phone,
        )
        db.add(request)
        db.add(Event(name="contact_shared", property_id=prop.id, user_id=session["user_id"], agency_id=agency.id, context={"direct": True, "billable": False}))
        db.commit()
        return {"id": req_id, "status": "SHARED", "phone": agency.phone, "billable": False}


@app.post("/agencies/{agency_id}/opt-out")
def agency_opt_out(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    """Baja permanente: la agencia deja de recibir contacto en frío o nuevas
    publicaciones vinculadas por el crawler (ver doc 05). Es irreversible por
    diseño — quien quiera volver debe contactar soporte, no autoservicio."""
    if session["agency_id"] != agency_id:
        raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        agency = db.get(Agency, agency_id)
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        existing = None
        if agency.phone:
            existing = db.scalar(select(AgentSuppressionList).where(AgentSuppressionList.phone_e164 == agency.phone))
        if not existing:
            db.add(AgentSuppressionList(phone_e164=agency.phone, reason="Solicitado por el agente desde el dashboard"))
            db.commit()
        return {"status": "OPTED_OUT"}


@app.post("/contact-requests/{request_id}/share")
def share_contact(request_id: str, session: dict[str, Any] = Depends(require_agent)):
    with Session(engine) as db:
        request = db.get(ContactRequest, request_id)
        if not request or request.agency_id != session["agency_id"]: raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        agency = db.get(Agency, request.agency_id)
        request.status = "SHARED"
        request.shared_phone = agency.phone if agency else None
        db.add(Event(name="contact_shared", property_id=request.property_id, user_id=request.user_id, agency_id=request.agency_id, context={"billable": request.billable}))
        db.commit()
        return {"status": "SHARED", "phone": request.shared_phone}


@app.get("/agencies/{agency_id}/opportunities")
def opportunities(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        property_ids = [p.id for p in db.scalars(select(Property).where(Property.agency_id == agency_id)).all()]
        events = db.scalars(select(Event).where(Event.agency_id == agency_id).order_by(Event.created_at.desc())).all()
        active = len({e.user_id for e in events if e.user_id})
        return {"active": active, "eventCount": len(events), "opportunities": [{"id":e.id,"property_id":e.property_id,"user_id":e.user_id,"event":e.name,"created_at":e.created_at.isoformat(),"context":e.context} for e in events[:50]], "propertyIds": property_ids}


@app.get("/agencies/{agency_id}")
def agency(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        return {"id":a.id,"name":a.name,"city":a.city,"verified":a.verified,"claimed":a.claimed,"phone":a.phone}


@app.patch("/agencies/{agency_id}")
def update_agency(agency_id: str, payload: AgencyUpdate, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.name = payload.name.strip()
        db.commit()
        return {"id":a.id,"name":a.name,"verified":a.verified}


@app.post("/agencies/{agency_id}/relink-by-phone")
def relink_by_phone(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        count = relink_properties(db, agency_id, session["phone"])
        db.commit()
        props = db.scalars(select(Property).where(Property.agency_id == agency_id)).all()
        return {"count": count, "properties": [prop_dict(p) for p in props], "message": f"Encontramos {count} publicaciones nuevas vinculadas por teléfono." if count else "No encontramos publicaciones nuevas con ese teléfono."}


@app.post("/agencies/{agency_id}/claim")
def claim_agency(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.claimed = True
        db.commit()
        return {"id": a.id, "claimed": True}


@app.get("/analytics/summary")
def analytics(session: dict[str, Any] = Depends(require_agent)):
    with Session(engine) as db:
        ensure_seed(db)
        rows = db.execute(select(Event.name)).scalars().all()
        counts: dict[str, int] = {}
        for name in rows: counts[name] = counts.get(name, 0) + 1
        return {"properties": db.query(Property).count(), "events": db.query(Event).count(), "offers": db.query(Offer).count(), "funnel": counts}
