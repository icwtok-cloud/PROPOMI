from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import unicodedata
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Protocol

import jwt
import phonenumbers
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, create_engine, select, text, inspect, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .sms_vonage import VonageSMSError, send_otp_sms

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

def strip_contact_leaks(texto: str | None) -> str:
    """Etapa 2 (doc 05): a diferencia de `sanitize_free_text` (que RECHAZA texto
    tipeado por una persona con un error claro), el texto que trae el crawler
    desde el portal de origen no tiene a quién devolverle un error — se limpia
    en silencio, reemplazando cualquier coincidencia de teléfono/wsp/email/
    usuario de redes por un marcador neutro, para no bloquear la ingesta
    completa de una propiedad por un dato de contacto colado en la descripción
    original del portal."""
    if not texto:
        return ""
    limpio = texto
    for pattern in _LEAK_PATTERNS:
        limpio = pattern.sub("[dato de contacto oculto]", limpio)
    return limpio

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_format(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise HTTPException(status_code=400, detail="Ingresá un email válido.")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./propomi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
ENV = os.getenv("ENV", "development").lower()
JWT_SECRET = os.getenv("JWT_SECRET")
if ENV == "production" and not JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be configured in production")
JWT_SECRET = JWT_SECRET or "dev-only-change-me"
JWT_ALGORITHM = "HS256"
# Etapa 4 (sección 10 / doc 6.2 · panel de revisión manual de agencias):
# clave fija única, no por-usuario. Es intencionalmente simple (mínimo
# viable, según el plan maestro) — no reemplaza un sistema de roles de
# equipo interno, que queda para más adelante si hace falta.
ADMIN_KEY = os.getenv("ADMIN_KEY")
if ENV == "production" and not ADMIN_KEY:
    raise RuntimeError("ADMIN_KEY must be configured in production")
ADMIN_KEY = ADMIN_KEY or "dev-only-admin-key"
OTP_TTL_SECONDS = 5 * 60
OTP_RATE_WINDOW = 10 * 60
OTP_MAX_REQUESTS = 3
MAX_PROPERTY_IMAGES = 5  # doc 06.1: hasta 5 fotos por propiedad, decisión ya tomada
FREE_LEADS_ON_VERIFICATION = 10
# T8.7: ventana de prioridad en carrera multi-agente (ticket).
LISTING_GROUP_REVEAL_WINDOW_WITH_SUB_HOURS = 24
LISTING_GROUP_REVEAL_WINDOW_NO_SUB_HOURS = 6
ONBOARDING_TOKEN_DAYS = 14  # T6.2: token de onboarding expira a los 14 días  # doc 06.2.3 / 08: primeros 10 reveals gratis al verificarse
PROPERTY_FRESHNESS_DAYS = 60  # doc 05 (Etapa 2): filtro de cold-start — una propiedad
# que el crawler no vuelve a ver hace más de 60 días se considera potencialmente
# vendida/dada de baja en el portal de origen y se oculta de la búsqueda pública
# (no se borra: sigue en la base por si el crawler la vuelve a detectar y
# actualiza last_seen_at, momento en el que vuelve a aparecer sola).
# Etapa 2: Google Sign-In del comprador (sección 6.2.1). El Client ID no es un
# secreto (viaja igual al frontend en cada request de Google Identity
# Services), por eso es seguro tenerlo como default acá — pero en producción
# conviene setearlo también como variable de entorno en Render por prolijidad.
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "872860769498-kmja44702diqc74d733ite8etttvkqp8.apps.googleusercontent.com",
)

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
    # DEPRECATED: texto libre que mezclaba "hace cuánto la detectamos" con
    # "lo que el portal de origen declara". Se mantiene solo por compatibilidad
    # de datos viejos — usar detected_at (ya existía) + origin_published_at
    # (nuevo, abajo) para todo desarrollo nuevo. Ver doc 04.2 / 12.
    freshness: Mapped[str] = mapped_column(String(100))
    # Antigüedad declarada por el portal de origen tal cual viene (ej. "publicado
    # hace 3 días") — se preserva sin reinterpretar, separada de detected_at
    # (que es cuándo el crawler/seed de Propomi la vio por primera vez).
    origin_published_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(160))
    source_url: Mapped[str] = mapped_column(String(500), default="#")
    # DEPRECATED: una sola imagen. Se mantiene por compatibilidad hacia atrás
    # (frontends viejos que todavía lean `image`) — el dato real y de uso
    # nuevo es `images` (lista JSON de hasta 5 URLs). ensure_schema_columns
    # migra automáticamente image -> images=[image] en filas viejas.
    image: Mapped[str] = mapped_column(String(1000))
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_phone_raw: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_phone_normalized: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Etapa 2 (doc 05): dedup simple sin IA. Si el crawler ingresa una
    # propiedad que matchea la regla (mismo rango de precio + zona + surface
    # similar) contra otra ya existente, se marca para revisión manual en vez
    # de auto-fusionarse o auto-descartarse — decisión explícita de no
    # automatizar el merge/descarte todavía.
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    possible_duplicate_of: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Etapa 019 (plan maestro 6.1): cuando el dedup de la 011 encuentra que la
    # publicación "duplicada" es de OTRA agencia (no un error de carga de la
    # misma agencia), no es un dato sucio a revisar — es la misma propiedad
    # real ofrecida por varios agentes, caso ya decidido en el plan maestro
    # ("se fusionan en una ficha con precio en rango"). `listing_group_id`
    # agrupa esas filas sin fusionarlas físicamente (cada agencia sigue
    # dueña de su propia fila/oferta/reveal); el rango de precio se calcula
    # al leer, ver `GET /properties/{id}/group`.
    listing_group_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)


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
    # DEPRECATED en favor de verification_status — se mantiene por compatibilidad
    # con datos/código viejo. Ver verification_status para el estado real.
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)
    # Verificación en dos niveles (doc 06/10, etapa 1). Una agencia recién
    # "claimeada" empieza en PENDING: ya tiene dashboard básico (ve que tiene
    # leads esperando, sin detalle) pero no puede revelar contacto ni pagar
    # hasta pasar a VERIFIED por revisión manual (panel interno, etapa 4).
    verification_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | VERIFIED | REJECTED
    instagram: Mapped[str | None] = mapped_column(String(160), nullable=True)
    website_link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Prioridad de cola de verificación: quien ya se suscribió antes de
    # verificarse pasa primero (SLA 24hs para ese caso). Mayor = más prioridad.
    verification_priority: Mapped[int] = mapped_column(Integer, default=0)
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # DEPRECATED (tanda subscriptions/lead_credits): migradas a tablas propias.
    # Se mantienen hasta confirmar que todo lee/escribe las tablas nuevas.
    # Borrarlas es un paso posterior separado. Ver migrate_agency_monetization().
    subscription_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)  # DEPRECATED -> Subscription.plan
    plan_lead_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)  # DEPRECATED -> Subscription.cupo_ciclo
    leads_used_current_period: Mapped[int] = mapped_column(Integer, default=0)  # DEPRECATED -> Subscription.consumido_ciclo
    subscription_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # DEPRECATED
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # DEPRECATED
    free_leads_remaining: Mapped[int] = mapped_column(Integer, default=0)  # DEPRECATED -> LeadCredit
    # Etapa 4 del roadmap general (subdominios por agencia): identificador
    # público y estable para la URL de la agencia (ej. inmobiliaria-norte
    # -> inmobiliaria-norte.propomi.lat vía middleware Next.js). Se genera
    # una sola vez (ensure_agency_slugs / al crear la agencia) y nunca se
    # recalcula solo, para no romper links/subdominios ya compartidos si el
    # nombre de la agencia cambia después. Nullable por compatibilidad con
    # filas viejas hasta que corre el backfill.
    slug: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)


class AgencyPhone(Base):
    """Telefonos adicionales de una agencia (celular personal + linea de oficina, etc.).
    Agency.phone sigue siendo el telefono principal/original; esta tabla permite sumar
    mas sin romper la columna existente. relink-by-phone y el login por OTP buscan
    contra el conjunto Agency.phone + AgencyPhone.phone."""
    __tablename__ = "agency_phones"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(40), index=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SubscriptionPlan(str, Enum):
    """Planes de suscripción (doc PLAN_MAESTRO / T5).
    PAY_PER_LEAD = sin plan activo. PLAN_30/50/99 = packs mensuales.
    cupo: 30 / 60 / None(ilimitado). Valores reversibles si cambia pricing.
    """
    PAY_PER_LEAD = "PAY_PER_LEAD"
    PLAN_30 = "PLAN_30"
    PLAN_50 = "PLAN_50"
    PLAN_99 = "PLAN_99"


PLAN_CUPO: dict[str, int | None] = {
    SubscriptionPlan.PAY_PER_LEAD.value: 0,
    SubscriptionPlan.PLAN_30.value: 30,
    SubscriptionPlan.PLAN_50.value: 60,
    SubscriptionPlan.PLAN_99.value: None,
}


class Subscription(Base):
    """Plan activo por agencia — entidad propia (antes columnas en Agency)."""
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(40), index=True)
    plan: Mapped[str] = mapped_column(String(20))
    cupo_ciclo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consumido_ciclo: Mapped[int] = mapped_column(Integer, default=0)
    fecha_renovacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class LeadCredit(Base):
    """Créditos gratis de reveal al verificarse (antes Agency.free_leads_remaining)."""
    __tablename__ = "lead_credits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(40), index=True, unique=True)
    cupo: Mapped[int] = mapped_column(Integer, default=0)
    consumido: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.COMPRADOR.value)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Etapa 2 (sección 6.2.1): el celular se verifica reutilizando el sistema
    # de OTP existente (ver /auth/otp/verify-buyer); Google Sign-In se pide
    # después, como segunda prueba de identidad, recién antes de "Enviar
    # oferta". Ninguno de los dos reemplaza al otro — el teléfono sigue
    # siendo la identidad canónica del sistema (regla no negociable).
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    google_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
    # T9.3: canal de origen del link compartible (ej. "storefront", "wa-agente",
    # slug de agencia). Nunca texto libre del comprador — solo un código corto
    # validado. Permite al agente distinguir de qué canal vino cada oferta.
    origin: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Lead(Base):
    """Etapa (rediseño wizard): pregunta/visita calificadas por el mismo
    wizard que la oferta, pero sin forzar un monto — a diferencia de Offer,
    `amount` es opcional (solo existe si el comprador eligió proponer un
    precio desde el modo 'question'). No reusa la tabla `offers` a propósito:
    mezclar "sin propuesta de precio" dentro de un modelo pensado para
    ofertas ensuciaría ese esquema con campos que no le pertenecen. El resto
    de la calificación (capital, forma de pago, plazo, condicionantes) es
    igual que en Offer porque son los mismos pasos 2-4 del wizard."""
    __tablename__ = "leads"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    # QUESTION | VISIT
    intent_type: Mapped[str] = mapped_column(String(20))
    # Solo aplica a intent_type=QUESTION cuando el comprador NO tocó
    # "Todavía no tengo una propuesta" — si la tocó, has_proposal=False y
    # amount queda None. En VISIT siempre False/None.
    has_proposal: Mapped[bool] = mapped_column(Boolean, default=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    payment_form: Mapped[str | None] = mapped_column(String(30), nullable=True)
    capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Solo aplica a intent_type=VISIT. visit_day: fecha ISO (YYYY-MM-DD).
    # visit_slot: una de "08-12" | "12-16" | "16-20".
    visit_day: Mapped[str | None] = mapped_column(String(10), nullable=True)
    visit_slot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    buyer_name: Mapped[str] = mapped_column(String(120))
    buyer_phone_raw: Mapped[str] = mapped_column(String(40))
    buyer_phone_normalized: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    buyer_email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_revealed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
    offer_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    agency_id: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(30))
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | COMPLETED | FAILED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)




class ColdStartTask(Base):
    """T6.1: cuando llega una oferta real sobre una propiedad de una agencia
    todavía no reclamada (o sin agency_id pero con teléfono scrapeado), se
    genera una tarea de notificación manual. El envío es 100% humano al
    principio. El teléfono scrapeado NUNCA viaja en endpoints públicos —
    solo en GET /admin/cold-start/pending (X-Admin-Key)."""
    __tablename__ = "cold_start_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(40), index=True)
    property_id: Mapped[str] = mapped_column(String(40), index=True)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # Teléfono scrapeado / de la agencia no reclamada — solo para el equipo
    # interno que manda el mensaje a mano. Nunca en API pública.
    target_phone: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    property_title: Mapped[str] = mapped_column(String(200))
    property_zone: Mapped[str] = mapped_column(String(100))
    # Token de un solo uso para /onboarding/{token} (T6.2); se invalida al claim.
    onboarding_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | SENT | CLAIMED | EXPIRED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)

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
            # Etapa 1: imágenes múltiples + fecha de origen separada de
            # freshness. SQLite/Postgres guardan `images` como TEXT;
            # SQLAlchemy JSON serializa/deserializa igual para ambos motores
            # sin necesitar un tipo nativo json en la columna.
            "images": "TEXT DEFAULT '[]'",
            "origin_published_at": "VARCHAR(100)",
            "needs_review": "BOOLEAN DEFAULT FALSE",
            "possible_duplicate_of": "VARCHAR(40)",
            "listing_group_id": "VARCHAR(40)",
        },
        "agencies": {
            "phone": "VARCHAR(30)",
            "verification_status": "VARCHAR(20) DEFAULT 'PENDING'",
            "instagram": "VARCHAR(160)",
            "website_link": "VARCHAR(300)",
            "verification_priority": "INTEGER DEFAULT 0",
            "verification_reviewed_at": "TIMESTAMP",
            "verification_notes": "VARCHAR(300)",
            "subscription_tier": "VARCHAR(20)",
            "plan_lead_quota": "INTEGER",
            "leads_used_current_period": "INTEGER DEFAULT 0",
            "subscription_started_at": "TIMESTAMP",
            "current_period_start": "TIMESTAMP",
            "free_leads_remaining": "INTEGER DEFAULT 0",
            "slug": "VARCHAR(160)",
        },
        "contact_requests": {
            "requester_role": "VARCHAR(20) DEFAULT 'COMPRADOR'",
            "billable": "BOOLEAN DEFAULT TRUE",
            "shared_phone": "VARCHAR(30)",
        },
        "otp_codes": {"verify_attempts": "INTEGER DEFAULT 0"},
        "reveal_transactions": {"lead_id": "VARCHAR(40)"},
        "users": {
            "phone_verified_at": "TIMESTAMP",
            "email": "VARCHAR(160)",
            "google_sub": "VARCHAR(120)",
            "google_verified_at": "TIMESTAMP",
        },
        "offers": {
            "buyer_name": "VARCHAR(120) DEFAULT ''",
            "buyer_phone_raw": "VARCHAR(40) DEFAULT ''",
            "buyer_phone_normalized": "VARCHAR(30)",
            "buyer_email": "VARCHAR(160)",
            "contact_revealed": "BOOLEAN DEFAULT FALSE",
            "contact_revealed_at": "TIMESTAMP",
            "origin": "VARCHAR(80)",
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

        # Etapa (rediseño wizard): reveal_transactions.offer_id era NOT NULL
        # cuando solo existian reveals de Offer. Ahora tambien puede haber
        # reveals de Lead (lead_id en su lugar), asi que offer_id debe poder
        # ser NULL. Postgres soporta ALTER COLUMN DROP NOT NULL directo;
        # SQLite no, asi que se omite ahi (uso local/dev, no produccion).
        if inspector.has_table("reveal_transactions") and conn.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE reveal_transactions ALTER COLUMN offer_id DROP NOT NULL"))




def migrate_legacy_property_images() -> None:
    """Decisión explícita (doc 04.2 / 06): migrar el dato viejo en vez de
    arrancar de cero. Toda fila que todavía tenga `images` vacío pero sí
    tenga el `image` (string) viejo, pasa a `images=[image]`. Es idempotente:
    una vez migrada, `images` deja de estar vacío y no se vuelve a tocar."""
    with Session(engine) as db:
        rows = db.scalars(select(Property)).all()
        changed = False
        for p in rows:
            if not p.images and p.image:
                p.images = [p.image][:MAX_PROPERTY_IMAGES]
                changed = True
        if changed:
            db.commit()



def migrate_agency_monetization() -> None:
    """Migra columnas Agency -> subscriptions / lead_credits. Idempotente. NO borra columnas viejas."""
    with Session(engine) as db:
        agencies = db.scalars(select(Agency)).all()
        changed = False
        for a in agencies:
            existing_lc = db.scalar(select(LeadCredit).where(LeadCredit.agency_id == a.id))
            if existing_lc is None:
                cupo = max(0, int(a.free_leads_remaining or 0))
                db.add(LeadCredit(id=f"lc-{uuid.uuid4().hex[:12]}", agency_id=a.id, cupo=cupo, consumido=0))
                changed = True
            existing_sub = db.scalar(select(Subscription).where(Subscription.agency_id == a.id))
            if existing_sub is None and a.subscription_tier:
                tier = a.subscription_tier
                plan_map = {
                    "30": "PLAN_30", "50": "PLAN_50", "99": "PLAN_99",
                    "PLAN_30": "PLAN_30", "PLAN_50": "PLAN_50", "PLAN_99": "PLAN_99",
                    "pay_per_lead": "PAY_PER_LEAD", "PAY_PER_LEAD": "PAY_PER_LEAD",
                    "STARTER": "PLAN_50",  # legacy test name
                }
                plan = plan_map.get(tier, tier if tier in PLAN_CUPO else "PAY_PER_LEAD")
                cupo = a.plan_lead_quota if a.plan_lead_quota is not None else PLAN_CUPO.get(plan)
                if plan == "PLAN_99":
                    cupo = None
                db.add(Subscription(
                    id=f"sub-{uuid.uuid4().hex[:12]}", agency_id=a.id, plan=plan,
                    cupo_ciclo=cupo, consumido_ciclo=max(0, int(a.leads_used_current_period or 0)),
                    fecha_renovacion=(a.current_period_start + timedelta(days=30)) if a.current_period_start else None,
                ))
                changed = True
        if changed:
            db.commit()


def get_lead_credit(db: Session, agency_id: str) -> LeadCredit | None:
    return db.scalar(select(LeadCredit).where(LeadCredit.agency_id == agency_id))


def get_subscription(db: Session, agency_id: str) -> Subscription | None:
    return db.scalar(select(Subscription).where(Subscription.agency_id == agency_id))


def get_available_credit(db: Session, agency_id: str) -> int:
    """Único punto de verdad del cupo de reveal. Fallback a columnas DEPRECATED si no hay filas nuevas."""
    total = 0
    lc = get_lead_credit(db, agency_id)
    sub = get_subscription(db, agency_id)
    if lc is None and sub is None:
        agency = db.get(Agency, agency_id)
        if not agency:
            return 0
        total += max(0, int(agency.free_leads_remaining or 0))
        if agency.subscription_tier:
            if agency.plan_lead_quota is None:
                return total + 10_000_000
            total += max(0, int(agency.plan_lead_quota) - int(agency.leads_used_current_period or 0))
        return total
    if lc:
        total += max(0, (lc.cupo or 0) - (lc.consumido or 0))
    if sub and sub.plan != SubscriptionPlan.PAY_PER_LEAD.value:
        if sub.cupo_ciclo is None:
            return total + 10_000_000
        total += max(0, (sub.cupo_ciclo or 0) - (sub.consumido_ciclo or 0))
    return total


def consume_reveal_credit(db: Session, agency: Agency) -> str | None:
    """Consume 1 cupo: lead_credits primero, luego subscriptions. Fallback legacy. Sync deprecated cols."""
    now = datetime.now(timezone.utc)
    lc = get_lead_credit(db, agency.id)
    sub = get_subscription(db, agency.id)
    if lc is None and sub is None:
        if (agency.free_leads_remaining or 0) > 0:
            agency.free_leads_remaining -= 1
            return "free_credit"
        if agency.subscription_tier and (
            agency.plan_lead_quota is None
            or (agency.leads_used_current_period or 0) < agency.plan_lead_quota
        ):
            agency.leads_used_current_period = (agency.leads_used_current_period or 0) + 1
            return "subscription_quota"
        return None
    if lc and (lc.cupo - lc.consumido) > 0:
        lc.consumido += 1
        lc.updated_at = now
        agency.free_leads_remaining = max(0, lc.cupo - lc.consumido)
        return "free_credit"
    if sub and sub.plan != SubscriptionPlan.PAY_PER_LEAD.value:
        if sub.cupo_ciclo is None or (sub.consumido_ciclo < (sub.cupo_ciclo or 0)):
            sub.consumido_ciclo += 1
            sub.updated_at = now
            agency.leads_used_current_period = sub.consumido_ciclo
            agency.subscription_tier = sub.plan
            agency.plan_lead_quota = sub.cupo_ciclo
            return "subscription_quota"
    return None


ensure_schema_columns()
migrate_legacy_property_images()
migrate_agency_monetization()

app = FastAPI(title="Propomi API", version="1.5.0")
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


class VonageSmsSender:
    def send(self, phone: str, code: str) -> None:
        try:
            send_otp_sms(phone, code)
        except VonageSMSError as exc:
            # Fallo real de Vonage (credenciales, red, rechazo del SMS) debe
            # llegar al cliente como error — nunca como "ok:true" silencioso.
            raise HTTPException(status_code=502, detail=f"No pudimos enviar el SMS: {exc}") from exc


OTP_SMS_PROVIDER = os.getenv("OTP_SMS_PROVIDER", "dev").strip().lower()


def _select_sms_sender() -> SmsSender:
    if OTP_SMS_PROVIDER == "vonage":
        return VonageSmsSender()
    return MockSmsSender()


sms_sender: SmsSender = _select_sms_sender()
OTP_MAX_VERIFY_ATTEMPTS = 5


class PaymentGateway(Protocol):
    def charge(self, agency_id: str, amount_usd: float, reference: str) -> bool: ...

    def create_checkout(self, agency_id: str, amount_usd: float, reference: str) -> str | None:
        """Devuelve una URL de checkout hosteado para que el agente complete
        el pago (etapa 017: Lemon Squeezy es redirect-based, no un cobro
        síncrono con tarjeta guardada). None si el gateway no soporta esto
        (ej. el mock) — en ese caso el 402 de /offers/{id}/reveal no incluye
        checkout_url."""
        ...


class MockPaymentGateway:
    """Seam para una pasarela real. A propósito NUNCA aprueba un cobro por sí
    sola — devuelve False siempre, para que jamás se revele un contacto
    'gratis' por accidente mientras no haya una integración real. En
    desarrollo, el pago se completa manualmente vía
    POST /payments/{transaction_id}/mock-complete (bloqueado en producción)."""
    def charge(self, agency_id: str, amount_usd: float, reference: str) -> bool:
        if ENV != "production":
            print(f"[PROPOMI PAYMENT MOCK] Cobro pendiente: agencia={agency_id} monto=USD{amount_usd} ref={reference}")
        return False

    def create_checkout(self, agency_id: str, amount_usd: float, reference: str) -> str | None:
        return None


# --- Etapa 017: Lemon Squeezy como pasarela de pago real para pay-per-lead ---
# Se eligió Lemon Squeezy (decisión del usuario, no Mercado Pago/Stripe como
# se había anotado en el "próximo paso lógico" de la etapa 016) porque actúa
# como Merchant of Record — cobra la tarjeta él mismo con un checkout
# hosteado y confirma el pago vía webhook, en vez de un `charge()` síncrono
# como asumía el diseño original del Protocol (por eso se agregó
# `create_checkout` arriba, sin romper `charge()` para el mock/tests).
LEMON_SQUEEZY_API_KEY = os.getenv("LEMON_SQUEEZY_API_KEY") or os.getenv("LEMONSQUEEZY_API_KEY")
LEMON_SQUEEZY_STORE_ID = os.getenv("LEMON_SQUEEZY_STORE_ID") or os.getenv("LEMONSQUEEZY_STORE_ID")
# Reveal (pay-per-lead) — compat con LEMON_SQUEEZY_VARIANT_ID legacy
LEMON_SQUEEZY_VARIANT_ID = (
    os.getenv("LS_VARIANT_REVEAL")
    or os.getenv("LEMON_SQUEEZY_VARIANT_ID")
)
# Planes de suscripción (env names del brief + alias)
LS_VARIANT_PLAN_BASIC = os.getenv("LS_VARIANT_PLAN_BASIC") or os.getenv("LS_VARIANT_SUB_30")
LS_VARIANT_PLAN_PRO = os.getenv("LS_VARIANT_PLAN_PRO") or os.getenv("LS_VARIANT_SUB_60")
LS_VARIANT_PLAN_PREMIUM = os.getenv("LS_VARIANT_PLAN_PREMIUM") or os.getenv("LS_VARIANT_SUB_UNLIMITED")
LEMON_SQUEEZY_WEBHOOK_SECRET = (
    os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET")
    or os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
    or os.getenv("LS_WEBHOOK_SECRET")
)
LEMON_SQUEEZY_API_BASE = "https://api.lemonsqueezy.com/v1"

# variant_id str -> (plan SubscriptionPlan value, cupo)
_LS_VARIANT_TO_PLAN: dict[str, tuple[str, int | None]] = {}
if LS_VARIANT_PLAN_BASIC:
    _LS_VARIANT_TO_PLAN[str(LS_VARIANT_PLAN_BASIC)] = (SubscriptionPlan.PLAN_30.value, 30)
if LS_VARIANT_PLAN_PRO:
    _LS_VARIANT_TO_PLAN[str(LS_VARIANT_PLAN_PRO)] = (SubscriptionPlan.PLAN_50.value, 60)
if LS_VARIANT_PLAN_PREMIUM:
    _LS_VARIANT_TO_PLAN[str(LS_VARIANT_PLAN_PREMIUM)] = (SubscriptionPlan.PLAN_99.value, None)


class LemonSqueezyPaymentGateway:
    """Pasarela real vía Lemon Squeezy. `charge()` siempre devuelve False
    (Lemon Squeezy es asíncrono: no hay forma de confirmar el cobro en el
    mismo request) — la confirmación real llega por
    POST /payments/webhooks/lemonsqueezy y de ahí se completa la
    RevealTransaction. `create_checkout()` crea el checkout hosteado y
    devuelve su URL para que el agente pague."""

    def charge(self, agency_id: str, amount_usd: float, reference: str) -> bool:
        return False

    def create_checkout(self, agency_id: str, amount_usd: float, reference: str) -> str | None:
        if not (LEMON_SQUEEZY_API_KEY and LEMON_SQUEEZY_STORE_ID and LEMON_SQUEEZY_VARIANT_ID):
            print("[PROPOMI LEMON SQUEEZY] Faltan variables de entorno (API_KEY/STORE_ID/VARIANT_ID) — no se puede crear el checkout.")
            return None
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        # transaction_id viaja en custom_data para poder
                        # identificar la RevealTransaction cuando llegue el webhook.
                        "custom": {"transaction_id": reference, "agency_id": agency_id, "kind": "reveal"},
                    },
                    "product_options": {"redirect_url": "https://propomi.lat/mi-cuenta?payment=ok"},
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": str(LEMON_SQUEEZY_STORE_ID)}},
                    "variant": {"data": {"type": "variants", "id": str(LEMON_SQUEEZY_VARIANT_ID)}},
                },
            }
        }
        req = urllib.request.Request(
            f"{LEMON_SQUEEZY_API_BASE}/checkouts",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
                "Authorization": f"Bearer {LEMON_SQUEEZY_API_KEY}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["data"]["attributes"]["url"]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as exc:
            print(f"[PROPOMI LEMON SQUEEZY] Error creando checkout para ref={reference}: {exc}")
            return None


def _select_payment_gateway() -> PaymentGateway:
    if LEMON_SQUEEZY_API_KEY and LEMON_SQUEEZY_STORE_ID and LEMON_SQUEEZY_VARIANT_ID:
        return LemonSqueezyPaymentGateway()
    if ENV == "production":
        # Sin credenciales de Lemon Squeezy en producción, seguimos con el
        # mock: sigue sin revelar nada gratis, solo que ningún pago real
        # puede procesarse hasta que se configuren las 3 variables de arriba.
        print("[PROPOMI LEMON SQUEEZY] ENV=production sin credenciales configuradas — usando MockPaymentGateway (todo pay-per-lead quedará 402 sin checkout_url).")
    return MockPaymentGateway()


payment_gateway: PaymentGateway = _select_payment_gateway()
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


def slugify(name: str) -> str:
    """Etapa 4 (subdominios por agencia): normaliza un nombre de agencia a un
    slug apto para subdominio (minúsculas, sin acentos, solo [a-z0-9-]).
    No garantiza unicidad por sí sola — eso lo resuelve el caller agregando
    un sufijo numérico (ver ensure_agency_slugs)."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "agencia"


def ensure_agency_slugs(db: Session) -> None:
    """Backfill de slugs para agencias creadas antes de que existiera la
    columna (o cualquier fila que por algún motivo haya quedado sin slug).
    Se corre en cada request a los endpoints públicos de agencia (barato:
    solo hace algo si hay filas con slug NULL) en vez de una migración
    one-shot, para no depender de un script aparte que el usuario tendría
    que acordarse de correr una vez."""
    pending = db.scalars(select(Agency).where(Agency.slug.is_(None))).all()
    if not pending:
        return
    existing = {s for (s,) in db.execute(select(Agency.slug).where(Agency.slug.isnot(None))).all()}
    for a in pending:
        base = slugify(a.name)
        candidate = base
        n = 2
        while candidate in existing:
            candidate = f"{base}-{n}"
            n += 1
        a.slug = candidate
        existing.add(candidate)
    db.commit()


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


def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    """Etapa 4: clave fija de administración para el panel interno de
    revisión de agencias. Va en el header `X-Admin-Key`, nunca en la URL
    (para no quedar en logs de acceso ni en el historial del navegador)."""
    if not x_admin_key or not secrets.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(status_code=401, detail="Clave de administración inválida")


# --------------------------------------------------------------------------
# Etapa 2 (doc 05): ingesta del crawler. Un único endpoint recibe tanto altas
# nuevas como "el crawler volvió a ver esta misma publicación" (upsert por
# source+source_url, que es la identidad natural de una publicación en su
# portal de origen). Protegido con la misma clave admin que el panel de
# verificación — no es público, lo llama únicamente el proceso del crawler.
# --------------------------------------------------------------------------
DEDUP_PRICE_TOLERANCE = 0.05  # ±5% de precio
DEDUP_SURFACE_TOLERANCE = 0.10  # ±10% de superficie


class PropertyIngestIn(BaseModel):
    source: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=200)
    type: str = "Departamento"
    operation: str = "Venta"
    price: float = Field(gt=0)
    currency: str = "USD"
    zone: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    country: str = "Argentina"
    surface: float = Field(gt=0)
    rooms: int = Field(ge=0)
    bedrooms: int = 1
    bathrooms: int = 1
    parking: bool = False
    pool: bool = False
    balcony: bool = False
    pet_friendly: bool = False
    credit: bool = False
    origin_published_at: str | None = None
    images: list[str] = Field(default_factory=list)
    description: str = ""
    agency_id: str | None = None
    contact_phone_raw: str | None = None

    @field_validator("images")
    @classmethod
    def cap_images(cls, v: list[str]) -> list[str]:
        return v[:MAX_PROPERTY_IMAGES]



class PropertyCreateIn(BaseModel):
    """Alta manual de propiedad por un agente verificado (T7.1 / T7.2 backend).
    No es ingesta de crawler: el agente escribe los datos, agency_id se fuerza
    a la sesión, y la descripción pasa por sanitize_free_text (rechaza fugas)."""
    title: str = Field(min_length=1, max_length=200)
    type: str = "Departamento"
    operation: str = "Venta"
    price: float = Field(gt=0)
    currency: str = "USD"
    zone: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    country: str = "Argentina"
    surface: float = Field(gt=0)
    rooms: int = Field(ge=0)
    bedrooms: int = 1
    bathrooms: int = 1
    parking: bool = False
    pool: bool = False
    balcony: bool = False
    pet_friendly: bool = False
    credit: bool = False
    images: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("images")
    @classmethod
    def cap_images(cls, v: list[str]) -> list[str]:
        return v[:MAX_PROPERTY_IMAGES]


def find_possible_duplicate(db: Session, zone: str, price: float, surface: float, exclude_id: str | None = None) -> Property | None:
    """Regla de dedup simple pedida (doc 05, sin IA todavía): misma zona +
    precio dentro de ±5% + superficie dentro de ±10% de alguna propiedad ya
    existente -> se marca para revisión manual, nunca se fusiona ni descarta
    solo. Barrido en Python (no en SQL) a propósito: el volumen esperado por
    zona en esta etapa es chico y así queda fácil de leer/ajustar tolerancias."""
    lo, hi = price * (1 - DEDUP_PRICE_TOLERANCE), price * (1 + DEDUP_PRICE_TOLERANCE)
    stmt = select(Property).where(Property.zone == zone, Property.price >= lo, Property.price <= hi)
    for candidate in db.scalars(stmt).all():
        if exclude_id and candidate.id == exclude_id:
            continue
        if not candidate.surface:
            continue
        if abs(candidate.surface - surface) / candidate.surface <= DEDUP_SURFACE_TOLERANCE:
            return candidate
    return None


@app.post("/properties/ingest", status_code=201)
def ingest_property(payload: PropertyIngestIn, _: None = Depends(require_admin)):
    description = strip_contact_leaks(payload.description)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        existing = db.scalar(
            select(Property).where(Property.source == payload.source, Property.source_url == payload.source_url)
        )
        if existing:
            # Ya la conocíamos: es el mismo barrido volviendo a ver la misma
            # publicación. Se actualizan los datos que pueden cambiar entre
            # barridos y, sobre todo, `last_seen_at` (lo que alimenta el
            # filtro de frescura de PROPERTY_FRESHNESS_DAYS) — `detected_at`
            # NUNCA se toca acá, es la fecha de la primera vez que la vimos.
            existing.title = payload.title
            existing.type = payload.type
            existing.operation = payload.operation
            existing.price = payload.price
            existing.currency = payload.currency
            existing.city = payload.city
            existing.country = payload.country
            existing.surface = payload.surface
            existing.rooms = payload.rooms
            existing.bedrooms = payload.bedrooms
            existing.bathrooms = payload.bathrooms
            existing.parking = payload.parking
            existing.pool = payload.pool
            existing.balcony = payload.balcony
            existing.pet_friendly = payload.pet_friendly
            existing.credit = payload.credit
            existing.origin_published_at = payload.origin_published_at
            existing.images = payload.images
            existing.image = payload.images[0] if payload.images else existing.image
            existing.description = description
            if payload.contact_phone_raw:
                existing.contact_phone_raw = payload.contact_phone_raw
                existing.contact_phone_normalized = normalize_phone(payload.contact_phone_raw)
            existing.last_seen_at = now
            db.commit()
            return {"id": existing.id, "status": "updated", "needs_review": existing.needs_review, "possible_duplicate_of": existing.possible_duplicate_of}

        duplicate = find_possible_duplicate(db, payload.zone, payload.price, payload.surface)

        # Etapa 019: si el "duplicado" es de otra agencia, es multi-agente
        # sobre la misma propiedad real (plan maestro 6.1) — se agrupa por
        # listing_group_id, sin marcar needs_review (no es un error a
        # revisar). Si es de la MISMA agencia (o `duplicate` no tiene
        # agencia), se mantiene el comportamiento viejo de la etapa 011:
        # needs_review para que un admin lo confirme o descarte a mano.
        is_multi_agent_dup = bool(
            duplicate and duplicate.agency_id and payload.agency_id and duplicate.agency_id != payload.agency_id
        )
        group_id = None
        if is_multi_agent_dup:
            group_id = duplicate.listing_group_id or f"lg-{uuid.uuid4().hex[:12]}"
            if not duplicate.listing_group_id:
                duplicate.listing_group_id = group_id

        new_id = f"p-{uuid.uuid4().hex[:12]}"
        prop = Property(
            id=new_id, title=payload.title, type=payload.type, operation=payload.operation,
            price=payload.price, currency=payload.currency, zone=payload.zone, city=payload.city,
            country=payload.country, surface=payload.surface, rooms=payload.rooms,
            bedrooms=payload.bedrooms, bathrooms=payload.bathrooms, parking=payload.parking,
            pool=payload.pool, balcony=payload.balcony, pet_friendly=payload.pet_friendly,
            credit=payload.credit, freshness="", origin_published_at=payload.origin_published_at,
            source=payload.source, source_url=payload.source_url,
            image=(payload.images[0] if payload.images else ""), images=payload.images,
            description=description, agency_id=payload.agency_id,
            contact_phone_raw=payload.contact_phone_raw,
            contact_phone_normalized=normalize_phone(payload.contact_phone_raw) if payload.contact_phone_raw else None,
            detected_at=now, last_seen_at=now,
            needs_review=bool(duplicate) and not is_multi_agent_dup,
            possible_duplicate_of=duplicate.id if (duplicate and not is_multi_agent_dup) else None,
            listing_group_id=group_id,
        )
        db.add(prop)
        db.commit()
        return {
            "id": prop.id, "status": "created", "needs_review": prop.needs_review,
            "possible_duplicate_of": prop.possible_duplicate_of, "listing_group_id": prop.listing_group_id,
        }


DEMO = [
    {"id":"p1","title":"Departamento luminoso 2 ambientes","type":"Departamento","operation":"Venta","price":118000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":45,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":False,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 2 días","origin_published_at":"Publicado hace 2 días","source":"Inmobiliaria Norte","source_url":"#","image":"https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=85","images":["https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=85"],"description":"Unidad renovada, muy luminosa y con balcón.","agency_id":"a1","contact_phone_raw":"11 5555-0101"},
    {"id":"p2","title":"Departamento moderno con balcón","type":"Departamento","operation":"Venta","price":120000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":43,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":True,"pool":False,"balcony":True,"pet_friendly":False,"credit":True,"freshness":"Actualizada hace 4 días","origin_published_at":"Publicado hace 4 días","source":"Red Urbana","source_url":"#","image":"https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1000&q=85","images":["https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1000&q=85"],"description":"Edificio moderno con cochera y amenities.","agency_id":"a2","contact_phone_raw":"+54 9 11 5555-0202"},
    {"id":"p3","title":"2 ambientes amplio a estrenar","type":"Departamento","operation":"Venta","price":125000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":48,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":True,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 6 días","origin_published_at":"Publicado hace 6 días","source":"Habitar","source_url":"#","image":"https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=85","images":["https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=85"],"description":"A estrenar, excelente distribución.","agency_id":"a1","contact_phone_raw":"11 5555-0101"},
    {"id":"p4","title":"Departamento 3 ambientes con patio","type":"Departamento","operation":"Venta","price":138000,"currency":"USD","zone":"Villa Crespo","city":"Buenos Aires","surface":62,"rooms":3,"bedrooms":2,"bathrooms":1,"parking":False,"pool":False,"balcony":False,"pet_friendly":True,"credit":True,"freshness":"Actualizada hace 1 día","origin_published_at":"Publicado hace 1 día","source":"Urbania","source_url":"#","image":"https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1000&q=85","images":["https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1000&q=85"],"description":"Patio y ambientes amplios para familia.","agency_id":"a3","contact_phone_raw":"11 5555-0303"},
]


ALLOWED_EVENTS = {
    "property_view", "property_save", "property_compare", "property_question",
    "visit_request", "offer_created", "contact_requested", "contact_shared",
    "counter_offer_created", "negotiation_started", "operation_advanced",
    # Etapa 3 (sección 10 / fase Intelligence): búsquedas/filtros del
    # comprador. Se loguea automáticamente desde GET /properties (ver más
    # abajo) y también queda permitido acá por si el frontend alguna vez
    # necesita loguearlo manual vía POST /events.
    "search_performed",
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
    # T9.3: código de canal (solo [a-z0-9_-], máx 80). No es texto libre.
    origin: str | None = Field(default=None, max_length=80)

    @field_validator("comment")
    @classmethod
    def check_comment_leak(cls, v: str | None) -> str | None:
        return sanitize_free_text(v, campo="comentario")

    @field_validator("origin")
    @classmethod
    def check_origin(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", v):
            raise HTTPException(status_code=400, detail="Origen inválido.")
        return v

    @field_validator("buyer_email")
    @classmethod
    def check_email_format(cls, v: str | None) -> str | None:
        return validate_email_format(v)


VALID_VISIT_SLOTS = {"08-12", "12-16", "16-20"}


class LeadIn(BaseModel):
    property_id: str
    intent_type: str  # QUESTION | VISIT
    has_proposal: bool = False
    amount: float | None = None
    payment_form: str | None = None
    capital: float | None = None
    timeframe: str | None = None
    comment: str | None = Field(default=None, max_length=500)
    visit_day: str | None = None  # YYYY-MM-DD, solo intent_type=VISIT
    visit_slot: str | None = None  # "08-12" | "12-16" | "16-20", solo intent_type=VISIT
    buyer_name: str = Field(min_length=2, max_length=120)
    buyer_phone: str = Field(min_length=6, max_length=40)
    buyer_email: str | None = Field(default=None, max_length=160)
    origin: str | None = Field(default=None, max_length=80)

    @field_validator("intent_type")
    @classmethod
    def check_intent_type(cls, v: str) -> str:
        if v not in ("QUESTION", "VISIT"):
            raise HTTPException(status_code=400, detail="intent_type debe ser 'QUESTION' o 'VISIT'")
        return v

    @field_validator("comment")
    @classmethod
    def check_comment_leak(cls, v: str | None) -> str | None:
        return sanitize_free_text(v, campo="comentario")

    @field_validator("origin")
    @classmethod
    def check_origin(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", v):
            raise HTTPException(status_code=400, detail="Origen inválido.")
        return v

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


class SubscriptionIn(BaseModel):
    """Registro/cambio de plan (dev/mock). En prod preferir checkout Lemon."""
    plan: str


class CheckoutRequestIn(BaseModel):
    """Checkout Lemon: reveal | plan_basic | plan_pro | plan_premium."""
    kind: str
    offer_id: str | None = None
    lead_id: str | None = None
    email: str | None = None


class AgencyUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    # Instagram es obligatorio para poder pasar de PENDING a VERIFIED (doc
    # 06.2.8), pero acá solo se captura el dato — el pasaje a VERIFIED lo hace
    # la revisión manual (panel interno, Etapa 4), no este endpoint.
    instagram: str | None = Field(default=None, max_length=160)
    website_link: str | None = Field(default=None, max_length=300)


class PhoneIn(BaseModel):
    phone: str = Field(min_length=6, max_length=40)


def ensure_seed(db: Session) -> None:
    if db.scalar(select(Property.id).limit(1)) is None:
        for row in DEMO:
            row = dict(row)
            row["contact_phone_normalized"] = normalize_phone(row["contact_phone_raw"])
            db.add(Property(**row))
        db.add_all([
            Agency(id="a1", name="Inmobiliaria Norte", slug="inmobiliaria-norte", city="Buenos Aires", verified=True, claimed=True, phone=normalize_phone("11 5555-0101"), verification_status="VERIFIED", instagram="@inmobiliarianorte", free_leads_remaining=FREE_LEADS_ON_VERIFICATION),
            Agency(id="a2", name="Red Urbana", slug="red-urbana", city="Buenos Aires", verified=True, claimed=False, phone=normalize_phone("+54 9 11 5555-0202"), verification_status="VERIFIED", instagram="@redurbana", free_leads_remaining=FREE_LEADS_ON_VERIFICATION),
            Agency(id="a3", name="Urbania", slug="urbania", city="Buenos Aires", verified=False, claimed=False, phone=normalize_phone("11 5555-0303"), verification_status="PENDING"),
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
    return {"status": "ok", "service": "propomi-api", "version": "1.4.0"}


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
    if ENV != "production" and OTP_SMS_PROVIDER != "vonage":
        response["dev_code"] = code
    return response


def consume_valid_otp(db: Session, phone: str, code: str) -> None:
    """Valida y consume el último código OTP vigente para `phone`. Lanza
    HTTPException si el código es inválido/vencido/excedido en intentos.
    Compartido por /auth/otp/verify (agente) y /auth/otp/verify-buyer
    (comprador, Etapa 2) para no duplicar la lógica de expiración, intentos y
    rate limit — el `OTPRequest`/generación del código sigue siendo el mismo
    para ambos roles, solo cambia qué se hace DESPUÉS de validar el código."""
    otp = db.scalar(select(OTPCode).where(OTPCode.phone == phone, OTPCode.consumed == False).order_by(OTPCode.created_at.desc()))
    otp_expires_at = otp.expires_at.replace(tzinfo=timezone.utc) if otp and otp.expires_at.tzinfo is None else (otp.expires_at if otp else None)
    if not otp or otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Código incorrecto o vencido")
    if otp.verify_attempts >= OTP_MAX_VERIFY_ATTEMPTS:
        otp.consumed = True
        db.commit()
        raise HTTPException(status_code=429, detail="Demasiados intentos. Solicitá un nuevo código más tarde.")
    if not secrets.compare_digest(otp.code_hash, hash_otp(code)):
        otp.verify_attempts += 1
        if otp.verify_attempts >= OTP_MAX_VERIFY_ATTEMPTS:
            otp.consumed = True
        db.commit()
        raise HTTPException(status_code=400, detail="Código incorrecto o vencido")
    otp.consumed = True


@app.post("/auth/otp/verify")
def verify_otp(payload: OTPVerify):
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Teléfono inválido")
    with Session(engine) as db:
        consume_valid_otp(db, phone, payload.code)
        user = db.scalar(select(User).where(User.phone == phone))
        agency = find_agency_by_phone(db, phone)
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


@app.post("/auth/otp/verify-buyer")
def verify_otp_buyer(payload: OTPVerify):
    """Etapa 2 / sección 6.2.1: verificación de celular del COMPRADOR,
    reutilizando el mismo sistema de OTP que ya usa el agente (misma tabla,
    mismo hash, mismo rate limit, mismo TTL — ver `consume_valid_otp`), pero
    sin exigir que el teléfono esté asociado a una agencia (a diferencia de
    /auth/otp/verify, que es exclusivo de agentes). El resultado reemplaza a
    la sesión 'guest' anónima del comprador por una sesión atada a su celular
    real verificado."""
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Teléfono inválido")
    with Session(engine) as db:
        consume_valid_otp(db, phone, payload.code)
        user = db.scalar(select(User).where(User.phone == phone))
        if user is None:
            # Primera vez que este teléfono aparece en el sistema como
            # comprador: se crea directo ya verificado (el OTP recién
            # consumido ES la prueba de verificación).
            user = User(id=f"u-{uuid.uuid4().hex[:12]}", phone=phone, role=Role.COMPRADOR.value)
            db.add(user)
            db.flush()
        # Si el teléfono ya existe como AGENTE, se reutiliza esa misma fila
        # (el teléfono es la identidad canónica, sección 5) — no se lo
        # "degrada" a comprador ni se le cambia el rol, esta verificación
        # solo confirma que el celular es suyo.
        user.phone_verified_at = datetime.now(timezone.utc)
        db.commit()
        token = create_token(user)
        return {
            "token": token,
            "user": {"id": user.id, "phone": user.phone, "role": user.role, "agency_id": user.agency_id},
            "phone_verified": True,
        }


class GoogleAuthIn(BaseModel):
    id_token: str


@app.post("/auth/google")
def link_google_identity(payload: GoogleAuthIn, session: dict[str, Any] = Depends(current_session)):
    """Etapa 2 / sección 6.2.1: segunda prueba de identidad del comprador,
    pedida recién en el último paso del wizard de oferta, ADEMÁS del celular
    verificado por OTP (nunca en su lugar). Requiere una sesión ya vigente
    (guest o comprador con celular verificado) — este endpoint solo VINCULA
    la cuenta de Google a esa sesión, no crea una identidad nueva por sí
    solo, para que nadie pueda ofertar solo con Google sin haber verificado
    un celular real."""
    try:
        idinfo = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        # Token mal formado, firma inválida, audience distinto o vencido —
        # esto sí es responsabilidad del cliente, 401.
        raise HTTPException(status_code=401, detail="Token de Google inválido o vencido") from exc
    except google_auth_exceptions.TransportError as exc:
        # No se pudo llegar a googleapis.com para bajar las claves públicas
        # de verificación — es un problema de red transitorio, no un token
        # inválido. 401 sería engañoso acá (el usuario reintentaría con el
        # mismo botón y volvería a fallar por la misma razón de red).
        raise HTTPException(status_code=503, detail="No pudimos verificar con Google en este momento. Probá de nuevo en unos segundos.") from exc
    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=400, detail="Tu cuenta de Google no tiene el email verificado.")
    google_sub = idinfo["sub"]
    email = idinfo.get("email")
    with Session(engine) as db:
        user = db.get(User, session.get("user_id"))
        if not user:
            raise HTTPException(status_code=401, detail="Sesión inválida")
        if not user.phone_verified_at:
            raise HTTPException(status_code=403, detail="Verificá tu celular antes de vincular Google.")
        other = db.scalar(select(User).where(User.google_sub == google_sub, User.id != user.id))
        if other:
            raise HTTPException(status_code=409, detail="Esta cuenta de Google ya está vinculada a otro usuario de Propomi.")
        user.google_sub = google_sub
        user.email = email
        user.google_verified_at = datetime.now(timezone.utc)
        db.commit()
        return {"email": email, "google_verified": True}


def find_agency_by_phone(db: Session, phone: str) -> Agency | None:
    """Busca una agencia por telefono principal o por cualquiera de sus AgencyPhone."""
    agency = db.scalar(select(Agency).where(Agency.phone == phone))
    if agency:
        return agency
    ap = db.scalar(select(AgencyPhone).where(AgencyPhone.phone == phone))
    if ap:
        return db.get(Agency, ap.agency_id)
    return None


def all_agency_phones(db: Session, agency_id: str) -> list[str]:
    """Telefono principal + todos los AgencyPhone de una agencia, sin duplicados."""
    agency = db.get(Agency, agency_id)
    phones = {agency.phone} if agency and agency.phone else set()
    phones |= {ap.phone for ap in db.scalars(select(AgencyPhone).where(AgencyPhone.agency_id == agency_id))}
    return [p for p in phones if p]


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
        "credit": p.credit, "freshness": p.freshness, "source": p.source, "sourceUrl": p.source_url,
        "image": p.image, "images": p.images or ([p.image] if p.image else []),
        "originPublishedAt": p.origin_published_at,
        "description": p.description, "agencyId": p.agency_id, "detectedAt": p.detected_at.isoformat(), "lastSeenAt": p.last_seen_at.isoformat(),
        "needsReview": p.needs_review, "possibleDuplicateOf": p.possible_duplicate_of,
        "listingGroupId": p.listing_group_id,
    }


@app.get("/properties/{property_id}/group")
def get_listing_group(property_id: str):
    """Etapa 019 (plan maestro 6.1): si esta propiedad está agrupada porque
    varias agencias publican la misma propiedad real, devuelve el resto del
    grupo + el rango de precio fusionado (min/max entre todas las filas del
    grupo, incluida esta). Público (mismo criterio que GET /properties: no
    expone contacto de agencia, solo lo que ya es público en otras
    pantallas). Si la propiedad no pertenece a ningún grupo, devuelve
    `grouped: false` en vez de 404 — no tener grupo es el caso normal, no un
    error."""
    with Session(engine) as db:
        prop = db.get(Property, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        if not prop.listing_group_id:
            return {"grouped": False, "members": [prop_dict(prop)], "priceMin": prop.price, "priceMax": prop.price}
        members = db.scalars(
            select(Property).where(Property.listing_group_id == prop.listing_group_id)
        ).all()
        prices = [m.price for m in members] or [prop.price]
        return {
            "grouped": True,
            "listingGroupId": prop.listing_group_id,
            "members": [prop_dict(m) for m in members],
            "priceMin": min(prices),
            "priceMax": max(prices),
        }


class ReviewResolutionIn(BaseModel):
    action: str  # "confirm_duplicate" | "not_duplicate"


@app.get("/properties/review-queue")
def review_queue(_: None = Depends(require_admin)):
    """Etapa 2 (doc 05): cola de revisión manual para lo que el dedup de
    `POST /properties/ingest` marcó como posible duplicado. Devuelve cada
    propiedad en cuestión junto con la candidata a duplicado, para poder
    compararlas lado a lado sin tener que consultar la base a mano."""
    with Session(engine) as db:
        flagged = db.scalars(select(Property).where(Property.needs_review == True)).all()  # noqa: E712
        items = []
        for p in flagged:
            candidate = db.get(Property, p.possible_duplicate_of) if p.possible_duplicate_of else None
            items.append({"property": prop_dict(p), "candidate": prop_dict(candidate) if candidate else None})
        return {"count": len(items), "items": items}


@app.post("/properties/{property_id}/review")
def resolve_review(property_id: str, payload: ReviewResolutionIn, _: None = Depends(require_admin)):
    """Resuelve una entrada de la cola de revisión:
    - "confirm_duplicate": es realmente el mismo aviso duplicado -> se oculta
      (no se borra: se limpia `agency_id`/`source_url` no, solo se saca de
      circulación bajándola de la búsqueda pública vía `last_seen_at` muy
      viejo, coherente con el mismo mecanismo que ya usa el filtro de
      frescura, en vez de inventar un segundo mecanismo de ocultamiento).
    - "not_duplicate": falso positivo del dedup -> se limpia la marca y sigue
      circulando normalmente."""
    if payload.action not in ("confirm_duplicate", "not_duplicate"):
        raise HTTPException(status_code=400, detail="action debe ser 'confirm_duplicate' o 'not_duplicate'")
    with Session(engine) as db:
        p = db.get(Property, property_id)
        if not p:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        if payload.action == "confirm_duplicate":
            p.last_seen_at = datetime.now(timezone.utc) - timedelta(days=PROPERTY_FRESHNESS_DAYS + 1)
            p.needs_review = False
        else:
            p.needs_review = False
            p.possible_duplicate_of = None
        db.commit()
        return {"id": p.id, "status": payload.action, "needsReview": p.needs_review}


@app.get("/properties")
def properties(
    zone: str | None = None, type: str | None = None, operation: str | None = None,
    rooms: int | None = None, max_price: float | None = None, parking: bool | None = None,
    credit: bool | None = None, agency_id: str | None = None,
    # Etapa 3 (sección 10 / fase Intelligence): session_id opcional del
    # frontend para poder agrupar búsquedas de una misma sesión anónima sin
    # necesitar login (mismo campo que ya usa POST /events). authorization
    # es opcional a propósito: la búsqueda funciona sin sesión, pero si hay
    # una sesión válida (agente o comprador) se guarda el user_id para
    # análisis de demanda, igual que en cualquier otro evento del sistema.
    session_id: str | None = None, authorization: str | None = Header(default=None),
):
    session = None
    if authorization:
        try:
            session = current_session(authorization)
        except HTTPException:
            # Token vencido/ inválido en una búsqueda no debe romper la
            # búsqueda en sí — solo se pierde la asociación a un user_id.
            session = None
    with Session(engine) as db:
        ensure_seed(db)
        stmt = select(Property)
        if zone: stmt = stmt.where(Property.zone == zone)
        if type: stmt = stmt.where(Property.type == type)
        if operation: stmt = stmt.where(Property.operation == operation)
        if rooms: stmt = stmt.where(Property.rooms == rooms)
        if max_price: stmt = stmt.where(Property.price <= max_price)
        if parking is not None: stmt = stmt.where(Property.parking == parking)
        if credit is not None: stmt = stmt.where(Property.credit == credit)
        if agency_id: stmt = stmt.where(Property.agency_id == agency_id)
        # Etapa 2 (doc 05): oculta de la búsqueda pública lo que el crawler
        # no ve hace más de PROPERTY_FRESHNESS_DAYS — no afecta a agency_id
        # (una agencia sigue viendo sus propias publicaciones en "Mi cuenta"
        # aunque estén stale, para que pueda notar y resolver el problema).
        if not agency_id:
            freshness_cutoff = datetime.now(timezone.utc) - timedelta(days=PROPERTY_FRESHNESS_DAYS)
            stmt = stmt.where(Property.last_seen_at >= freshness_cutoff)
        results = db.scalars(stmt).all()

        # Etapa 3: evento agregado y anónimo por cada búsqueda — insumo para
        # matching/recomendaciones/demanda/pricing (doc, sección 10, fase
        # Intelligence). No se guarda ningún dato nuevo de contacto ni texto
        # libre; solo los filtros ya públicos de la query y el resultado.
        filters_used = {
            k: v for k, v in {
                "zone": zone, "type": type, "operation": operation, "rooms": rooms,
                "max_price": max_price, "parking": parking, "credit": credit,
                "agency_id": agency_id,
            }.items() if v is not None
        }
        db.add(Event(
            name="search_performed",
            user_id=session.get("user_id") if session else None,
            agency_id=session.get("agency_id") if session else None,
            session_id=session_id,
            context={"filters": filters_used, "result_count": len(results)},
        ))
        db.commit()

        return [prop_dict(p) for p in results]


@app.get("/properties/{property_id}")
def property_detail(property_id: str):
    with Session(engine) as db:
        ensure_seed(db)
        p = db.get(Property, property_id)
        if not p: raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        return prop_dict(p)


@app.post("/properties", status_code=201)
def create_property(payload: PropertyCreateIn, session: dict[str, Any] = Depends(require_agent)):
    """T7.1/T7.2 (backend): alta manual de propiedad por un agente con
    verification_status=VERIFIED. agency_id se toma de la sesión (nunca del
    body). Descripción tipada por persona → sanitize_free_text (rechaza
    fugas). Si matchea dedup con otra agencia, se agrupa con listing_group_id
    (misma regla de la etapa 019); si matchea con la misma agencia, se marca
    needs_review."""
    with Session(engine) as db:
        agency = db.get(Agency, session["agency_id"])
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        if agency.verification_status != "VERIFIED":
            raise HTTPException(
                status_code=403,
                detail="Tu agencia todavía no está verificada. Solo agencias verificadas pueden cargar propiedades.",
            )
        description = sanitize_free_text(payload.description or "", campo="description") or ""
        images = list(payload.images or [])[:MAX_PROPERTY_IMAGES]
        cover = images[0] if images else ""
        now = datetime.now(timezone.utc)
        duplicate = find_possible_duplicate(db, payload.zone, payload.price, payload.surface)
        group_id = None
        needs_review = False
        possible_duplicate_of = None
        if duplicate:
            same_agency = duplicate.agency_id == agency.id
            if same_agency or not duplicate.agency_id or not agency.id:
                needs_review = True
                possible_duplicate_of = duplicate.id
            else:
                group_id = duplicate.listing_group_id or f"lg-{uuid.uuid4().hex[:12]}"
                if not duplicate.listing_group_id:
                    duplicate.listing_group_id = group_id
        prop = Property(
            id=f"p-{uuid.uuid4().hex[:12]}",
            title=payload.title.strip(),
            type=payload.type,
            operation=payload.operation,
            price=payload.price,
            currency=payload.currency,
            zone=payload.zone.strip(),
            city=payload.city.strip(),
            country=payload.country,
            surface=payload.surface,
            rooms=payload.rooms,
            bedrooms=payload.bedrooms,
            bathrooms=payload.bathrooms,
            parking=payload.parking,
            pool=payload.pool,
            balcony=payload.balcony,
            pet_friendly=payload.pet_friendly,
            credit=payload.credit,
            freshness="Publicada por la agencia",
            origin_published_at="Publicada en Propomi",
            source=agency.name,
            source_url="#",
            image=cover,
            images=images,
            description=description,
            agency_id=agency.id,
            contact_phone_raw=agency.phone,
            contact_phone_normalized=agency.phone,
            detected_at=now,
            last_seen_at=now,
            needs_review=needs_review,
            possible_duplicate_of=possible_duplicate_of,
            listing_group_id=group_id,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)
        return prop_dict(prop)



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
            profile = IntentProfile(id=f"i-{uuid.uuid4().hex[:12]}", user_id=user_id, property_id=payload.property_id, **payload.model_dump(exclude={"property_id"}))
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
        # Etapa 2 / sección 6.2.1: enforcement real del lado del servidor —
        # el paso de identidad del frontend es UX, esto es lo que de verdad
        # impide que una oferta se cree sin el celular verificado. Google es
        # opcional (no se exige server-side).
        buyer_user = db.get(User, session["user_id"])
        if not buyer_user or not buyer_user.phone_verified_at:
            raise HTTPException(status_code=403, detail="Verificá tu celular antes de enviar una oferta.")
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
        event_ctx: dict[str, Any] = {"amount": payload.amount}
        if getattr(payload, "origin", None):
            event_ctx["origin"] = payload.origin
        # T8.7: notificar a todas las agencias del listing_group a la vez.
        notify_ids = listing_group_member_agency_ids(db, p) or ({p.agency_id} if p.agency_id else set())
        for aid in notify_ids:
            db.add(Event(
                name="offer_created",
                property_id=p.id,
                user_id=session["user_id"],
                agency_id=aid,
                context={**event_ctx, "listing_group_id": p.listing_group_id},
            ))

        # T6.1 cold start: oferta real sobre agencia no reclamada (o sin
        # agency pero con teléfono scrapeado) → tarea de notificación manual.
        # Nunca incluye buyer_name/phone/email. El teléfono target solo vive
        # en esta tabla y se lee desde /admin/cold-start/pending.
        target_phone = None
        agency_id_for_task = p.agency_id
        if p.agency_id:
            agency_row = db.get(Agency, p.agency_id)
            if agency_row and not agency_row.claimed:
                target_phone = agency_row.phone or p.contact_phone_normalized or p.contact_phone_raw
        elif p.contact_phone_normalized or p.contact_phone_raw:
            target_phone = p.contact_phone_normalized or p.contact_phone_raw
        if target_phone:
            token = secrets.token_urlsafe(24)
            db.add(ColdStartTask(
                id=f"cs-{uuid.uuid4().hex[:12]}",
                offer_id=offer.id,
                property_id=p.id,
                agency_id=agency_id_for_task,
                target_phone=str(target_phone),
                amount=payload.amount,
                currency="USD",
                property_title=p.title,
                property_zone=p.zone,
                onboarding_token=token,
                status="PENDING",
            ))

        db.commit()
        return {"id": offer.id, "status": offer.status}


def validate_visit_slot(visit_day: str | None, visit_slot: str | None) -> None:
    """Backend valida estricto: visit_day dentro de los próximos 7 días
    (hoy incluido) y visit_slot uno de los tres valores fijos — mismo
    criterio de rechazo con 400 que ya usa OfferIn con `origin`."""
    if not visit_day or not visit_slot:
        raise HTTPException(status_code=400, detail="Elegí un día y una franja horaria para la visita.")
    if visit_slot not in VALID_VISIT_SLOTS:
        raise HTTPException(status_code=400, detail="Franja horaria inválida.")
    try:
        day = datetime.strptime(visit_day, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha de visita inválida.")
    today = datetime.now(timezone.utc).date()
    if day < today or day > today + timedelta(days=6):
        raise HTTPException(status_code=400, detail="Elegí un día dentro de los próximos 7 días.")


@app.post("/leads", status_code=201)
def create_lead(payload: LeadIn, session: dict[str, Any] = Depends(current_session)):
    if session.get("role") != Role.COMPRADOR.value:
        raise HTTPException(status_code=403, detail="Solo un comprador puede crear una consulta o visita")
    if payload.intent_type == "VISIT":
        validate_visit_slot(payload.visit_day, payload.visit_slot)
    if payload.intent_type == "QUESTION" and payload.has_proposal and (payload.amount is None or payload.amount <= 0):
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")
    buyer_phone_normalized = normalize_phone(payload.buyer_phone)
    if not buyer_phone_normalized:
        raise HTTPException(status_code=400, detail="Ingresá un teléfono de contacto válido")
    with Session(engine) as db:
        buyer_user = db.get(User, session["user_id"])
        if not buyer_user or not buyer_user.phone_verified_at:
            raise HTTPException(status_code=403, detail="Verificá tu celular antes de continuar.")
        p = db.get(Property, payload.property_id)
        if not p:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        lead_data = payload.model_dump(exclude={"buyer_phone"})
        lead = Lead(
            id=f"l-{uuid.uuid4().hex[:12]}",
            user_id=session["user_id"],
            buyer_phone_raw=payload.buyer_phone,
            buyer_phone_normalized=buyer_phone_normalized,
            **lead_data,
        )
        db.add(lead)
        event_name = "visit_request" if payload.intent_type == "VISIT" else "property_question"
        event_ctx: dict[str, Any] = {"intent_type": payload.intent_type}
        if payload.amount:
            event_ctx["amount"] = payload.amount
        if payload.origin:
            event_ctx["origin"] = payload.origin
        notify_ids = listing_group_member_agency_ids(db, p) or ({p.agency_id} if p.agency_id else set())
        for aid in notify_ids:
            db.add(Event(
                name=event_name,
                property_id=p.id,
                user_id=session["user_id"],
                agency_id=aid,
                context={**event_ctx, "listing_group_id": p.listing_group_id},
            ))
        db.commit()
        return {"id": lead.id, "status": lead.status}


@app.get("/leads")
def list_leads(session: dict[str, Any] = Depends(current_session)):
    """Mismo criterio de restricción que GET /offers: agencia no VERIFIED
    solo ve la cantidad, nunca detalle ni contacto."""
    with Session(engine) as db:
        stmt = select(Lead)
        if session.get("role") == Role.AGENTE.value:
            own_props = list(db.scalars(select(Property).where(Property.agency_id == session["agency_id"])).all())
            own_ids = [p.id for p in own_props]
            group_ids = list({p.listing_group_id for p in own_props if p.listing_group_id})
            group_prop_ids: list[str] = []
            if group_ids:
                group_prop_ids = [
                    p.id for p in db.scalars(
                        select(Property).where(Property.listing_group_id.in_(group_ids))
                    ).all()
                ]
            visible_ids = list(set(own_ids + group_prop_ids)) or ["__none__"]
            stmt = stmt.where(Lead.property_id.in_(visible_ids))
            agency = db.get(Agency, session["agency_id"]) if session.get("agency_id") else None
            leads = db.scalars(stmt.order_by(Lead.created_at.desc())).all()
            if not agency or agency.verification_status != "VERIFIED":
                return {
                    "verificationRequired": True,
                    "verificationStatus": (agency.verification_status if agency else "PENDING"),
                    "count": len(leads),
                    "leads": [],
                }
        else:
            stmt = stmt.where(Lead.user_id == session["user_id"])
            leads = db.scalars(stmt.order_by(Lead.created_at.desc())).all()

        result = []
        for l in leads:
            prop = db.get(Property, l.property_id)
            row = {
                "id": l.id, "user_id": l.user_id, "property_id": l.property_id,
                "intent_type": l.intent_type, "has_proposal": l.has_proposal, "amount": l.amount,
                "currency": l.currency, "payment_form": l.payment_form, "capital": l.capital,
                "timeframe": l.timeframe, "comment": l.comment,
                "visit_day": l.visit_day, "visit_slot": l.visit_slot,
                "status": l.status, "created_at": l.created_at.isoformat(),
                "contact_revealed": l.contact_revealed, "origin": l.origin,
                "property_title": prop.title if prop else None,
                "property_zone": prop.zone if prop else None,
                "listing_group_id": prop.listing_group_id if prop else None,
            }
            if l.contact_revealed:
                row["buyer_name"] = l.buyer_name
                row["buyer_phone"] = l.buyer_phone_raw
                row["buyer_email"] = l.buyer_email
            result.append(row)
        return result

@app.get("/offers")
def list_offers(status: str | None = None, session: dict[str, Any] = Depends(current_session)):
    """T4.5: un agente con verification_status != VERIFIED solo recibe la
    cantidad de ofertas esperando — nunca monto, propiedad ni ningún detalle.
    Compradores y agentes VERIFIED siguen recibiendo la lista completa
    (el contacto del comprador solo si contact_revealed)."""
    with Session(engine) as db:
        stmt = select(Offer)
        if session.get("role") == Role.AGENTE.value:
            own_props = list(db.scalars(select(Property).where(Property.agency_id == session["agency_id"])).all())
            own_ids = [p.id for p in own_props]
            group_ids = list({p.listing_group_id for p in own_props if p.listing_group_id})
            group_prop_ids: list[str] = []
            if group_ids:
                group_prop_ids = [
                    p.id for p in db.scalars(
                        select(Property).where(Property.listing_group_id.in_(group_ids))
                    ).all()
                ]
            visible_ids = list(set(own_ids + group_prop_ids)) or ["__none__"]
            stmt = stmt.where(Offer.property_id.in_(visible_ids))
            agency = db.get(Agency, session["agency_id"]) if session.get("agency_id") else None
            if status:
                stmt = stmt.where(Offer.status == status)
            offers = db.scalars(stmt.order_by(Offer.created_at.desc())).all()
            if not agency or agency.verification_status != "VERIFIED":
                # Solo conteo — sin ids, montos ni property_id (anti-fuga de detalle comercial
                # hasta verificación; el reveal ya estaba bloqueado en POST /offers/{id}/reveal).
                return {
                    "verificationRequired": True,
                    "verificationStatus": (agency.verification_status if agency else "PENDING"),
                    "count": len(offers),
                    "offers": [],
                }
        else:
            stmt = stmt.where(Offer.user_id == session["user_id"])
            if status:
                stmt = stmt.where(Offer.status == status)
            offers = db.scalars(stmt.order_by(Offer.created_at.desc())).all()

        result = []
        for o in offers:
            prop = db.get(Property, o.property_id)
            row = {
                "id": o.id, "user_id": o.user_id, "property_id": o.property_id,
                "amount": o.amount, "currency": o.currency, "payment_form": o.payment_form,
                "capital": o.capital, "timeframe": o.timeframe, "comment": o.comment,
                "status": o.status, "created_at": o.created_at.isoformat(),
                "contact_revealed": o.contact_revealed, "origin": getattr(o, "origin", None),
                # Contexto de la ficha (nunca contacto del comprador).
                "property_title": prop.title if prop else None,
                "property_zone": prop.zone if prop else None,
                "listing_group_id": prop.listing_group_id if prop else None,
            }
            if o.contact_revealed:
                row["buyer_name"] = o.buyer_name
                row["buyer_phone"] = o.buyer_phone_raw
                row["buyer_email"] = o.buyer_email
            result.append(row)
        return result


@app.post("/offers/{offer_id}/counter", status_code=201)
def counter_offer(offer_id: str, payload: CounterIn, session: dict[str, Any] = Depends(require_agent)):
    with Session(engine) as db:
        agency = db.get(Agency, session["agency_id"])
        if not agency or agency.verification_status != "VERIFIED":
            raise HTTPException(status_code=403, detail="Tu agencia todavía no está verificada. No podés responder ofertas hasta estar Verificada.")
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



def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def listing_group_member_agency_ids(db: Session, prop: Property) -> set[str]:
    if not prop.listing_group_id:
        return {prop.agency_id} if prop.agency_id else set()
    members = db.scalars(
        select(Property).where(Property.listing_group_id == prop.listing_group_id)
    ).all()
    return {m.agency_id for m in members if m.agency_id}


def agent_in_listing_group(db: Session, prop: Property, agency_id: str) -> bool:
    if prop.agency_id == agency_id:
        return True
    return agency_id in listing_group_member_agency_ids(db, prop)


def enforce_listing_group_reveal_priority(
    db: Session, prop: Property, agency: Agency, offer: Offer, now: datetime
) -> None:
    """T8.7: dentro de la ventana, solo la agencia con suscripción más antigua
    del grupo puede revelar. Pasada la ventana, cualquiera del grupo."""
    if not prop.listing_group_id:
        return
    agency_ids = listing_group_member_agency_ids(db, prop)
    if len(agency_ids) <= 1:
        return
    agencies = [a for a in (db.get(Agency, aid) for aid in agency_ids) if a]
    subscribers = [a for a in agencies if a.subscription_tier and a.subscription_started_at]
    window_h = (
        LISTING_GROUP_REVEAL_WINDOW_WITH_SUB_HOURS
        if subscribers
        else LISTING_GROUP_REVEAL_WINDOW_NO_SUB_HOURS
    )
    created = _aware(offer.created_at) or now
    age = now - created
    if age >= timedelta(hours=window_h):
        return
    if not subscribers:
        return
    oldest = min(subscribers, key=lambda a: _aware(a.subscription_started_at) or now)
    if agency.id != oldest.id:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Esta oferta está en una ficha multi-agente. Durante las primeras "
                f"{window_h}h tiene prioridad la agencia con la suscripción más antigua. "
                f"Podés reintentar cuando expire la ventana si el lead sigue disponible."
            ),
        )


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
        if not prop:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        # T8.7: cualquier agencia del listing_group puede competir por el reveal.
        if not agent_in_listing_group(db, prop, session["agency_id"]):
            raise HTTPException(status_code=403, detail="Oferta fuera de tu agencia")

        agency = db.get(Agency, session["agency_id"])
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")

        if offer.contact_revealed:
            winner = db.scalar(
                select(RevealTransaction).where(
                    RevealTransaction.offer_id == offer.id,
                    RevealTransaction.status == "COMPLETED",
                )
            )
            if winner and winner.agency_id == agency.id:
                return {
                    "buyer_name": offer.buyer_name,
                    "buyer_phone": offer.buyer_phone_raw,
                    "buyer_email": offer.buyer_email,
                    "already_revealed": True,
                }
            raise HTTPException(
                status_code=409,
                detail="Otro agente del grupo ya reveló el contacto de esta oferta.",
            )

        if agency.verification_status != "VERIFIED":
            raise HTTPException(
                status_code=403,
                detail="Tu agencia todavía no está verificada. Completá Instagram/link de tu perfil y esperá la revisión para poder revelar contactos.",
            )

        now = datetime.now(timezone.utc)
        enforce_listing_group_reveal_priority(db, prop, agency, offer, now)

        # Cupo único vía get_available_credit / consume_reveal_credit.
        method = consume_reveal_credit(db, agency)
        if method is not None:
            offer.contact_revealed = True
            offer.contact_revealed_at = now
            txn_method = "FREE_CREDIT" if method == "free_credit" else RevealMethod.SUBSCRIPTION_QUOTA.value
            db.add(RevealTransaction(
                id=f"rt-{uuid.uuid4().hex[:12]}", offer_id=offer.id, agency_id=agency.id,
                method=txn_method, amount_usd=0.0, status="COMPLETED", completed_at=now,
            ))
            db.add(Event(name="contact_revealed", property_id=prop.id, user_id=offer.user_id, agency_id=agency.id, context={"method": method}))
            db.commit()
            return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "buyer_email": offer.buyer_email, "method": method}

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
            checkout_url = payment_gateway.create_checkout(agency_id=agency.id, amount_usd=PAY_PER_LEAD_USD, reference=transaction_id)
            detail: dict[str, Any] = {
                "message": f"Se requiere pago de USD {PAY_PER_LEAD_USD} para revelar este contacto.",
                "transaction_id": transaction_id,
            }
            if checkout_url:
                detail["checkout_url"] = checkout_url
            raise HTTPException(status_code=402, detail=detail)
        offer.contact_revealed = True
        offer.contact_revealed_at = now
        db.commit()
        return {"buyer_name": offer.buyer_name, "buyer_phone": offer.buyer_phone_raw, "buyer_email": offer.buyer_email, "method": "pay_per_lead"}


@app.post("/leads/{lead_id}/reveal")
def reveal_lead_contact(lead_id: str, session: dict[str, Any] = Depends(require_agent)):
    """Espejo de POST /offers/{offer_id}/reveal, operando sobre Lead en vez
    de Offer. Mismas reglas: pertenencia a la agencia (o al listing_group),
    idempotencia si ya fue revelado, cupo de suscripcion/credito primero,
    pay-per-lead via PaymentGateway despues — nunca revela gratis por
    default."""
    with Session(engine) as db:
        lead = db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Consulta o visita no encontrada")
        prop = db.get(Property, lead.property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Propiedad no encontrada")
        if not agent_in_listing_group(db, prop, session["agency_id"]):
            raise HTTPException(status_code=403, detail="Fuera de tu agencia")

        agency = db.get(Agency, session["agency_id"])
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")

        if lead.contact_revealed:
            winner = db.scalar(
                select(RevealTransaction).where(
                    RevealTransaction.lead_id == lead.id,
                    RevealTransaction.status == "COMPLETED",
                )
            )
            if winner and winner.agency_id == agency.id:
                return {
                    "buyer_name": lead.buyer_name,
                    "buyer_phone": lead.buyer_phone_raw,
                    "buyer_email": lead.buyer_email,
                    "already_revealed": True,
                }
            raise HTTPException(
                status_code=409,
                detail="Otro agente del grupo ya revelo el contacto de esta consulta/visita.",
            )

        if agency.verification_status != "VERIFIED":
            raise HTTPException(
                status_code=403,
                detail="Tu agencia todavia no esta verificada. Completa Instagram/link de tu perfil y espera la revision para poder revelar contactos.",
            )

        now = datetime.now(timezone.utc)

        method = consume_reveal_credit(db, agency)
        if method is not None:
            lead.contact_revealed = True
            lead.contact_revealed_at = now
            txn_method = "FREE_CREDIT" if method == "free_credit" else RevealMethod.SUBSCRIPTION_QUOTA.value
            db.add(RevealTransaction(
                id=f"rt-{uuid.uuid4().hex[:12]}", lead_id=lead.id, agency_id=agency.id,
                method=txn_method, amount_usd=0.0, status="COMPLETED", completed_at=now,
            ))
            db.add(Event(name="contact_revealed", property_id=prop.id, user_id=lead.user_id, agency_id=agency.id, context={"method": method, "lead": True}))
            db.commit()
            return {"buyer_name": lead.buyer_name, "buyer_phone": lead.buyer_phone_raw, "buyer_email": lead.buyer_email, "method": method}

        existing_paid = db.scalar(
            select(RevealTransaction).where(
                RevealTransaction.lead_id == lead.id,
                RevealTransaction.status == "COMPLETED",
            )
        )
        if existing_paid:
            lead.contact_revealed = True
            lead.contact_revealed_at = now
            db.commit()
            return {"buyer_name": lead.buyer_name, "buyer_phone": lead.buyer_phone_raw, "buyer_email": lead.buyer_email, "method": "pay_per_lead"}

        transaction_id = f"rt-{uuid.uuid4().hex[:12]}"
        charged = payment_gateway.charge(agency_id=agency.id, amount_usd=PAY_PER_LEAD_USD, reference=transaction_id)
        db.add(RevealTransaction(
            id=transaction_id, lead_id=lead.id, agency_id=agency.id,
            method=RevealMethod.PAY_PER_LEAD.value, amount_usd=PAY_PER_LEAD_USD,
            status="COMPLETED" if charged else "PENDING",
            completed_at=now if charged else None,
        ))
        db.commit()

        if not charged:
            checkout_url = payment_gateway.create_checkout(agency_id=agency.id, amount_usd=PAY_PER_LEAD_USD, reference=transaction_id)
            detail: dict[str, Any] = {
                "message": f"Se requiere pago de USD {PAY_PER_LEAD_USD} para revelar este contacto.",
                "transaction_id": transaction_id,
            }
            if checkout_url:
                detail["checkout_url"] = checkout_url
            raise HTTPException(status_code=402, detail=detail)
        lead.contact_revealed = True
        lead.contact_revealed_at = now
        db.commit()
        return {"buyer_name": lead.buyer_name, "buyer_phone": lead.buyer_phone_raw, "buyer_email": lead.buyer_email, "method": "pay_per_lead"}

@app.get("/payments/{transaction_id}/status")
def payment_status(transaction_id: str, session: dict[str, Any] = Depends(require_agent)):
    """Etapa 017/018: permite que el frontend pregunte '¿ya se confirmó?'
    después de volver de un checkout de Lemon Squeezy, sin tener que generar
    un checkout nuevo cada vez (a diferencia de reintentar
    POST /offers/{id}/reveal directamente, que crearía una transacción
    nueva si todavía no se pagó). Nunca revela nada acá — solo dice si el
    pago quedó COMPLETED; el reveal real sigue pasando por
    POST /offers/{id}/reveal, que ya sabe devolver el contacto sin volver a
    cobrar cuando encuentra una transacción COMPLETED (idempotencia)."""
    with Session(engine) as db:
        txn = db.get(RevealTransaction, transaction_id)
        if not txn or txn.agency_id != session["agency_id"]:
            raise HTTPException(status_code=404, detail="Transacción no encontrada")
        return {"status": txn.status}


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


def _ls_create_checkout_url(variant_id: str, agency_id: str, custom: dict[str, str], email: str | None = None) -> str | None:
    if not (LEMON_SQUEEZY_API_KEY and LEMON_SQUEEZY_STORE_ID and variant_id):
        return None
    checkout_data: dict[str, Any] = {"custom": custom}
    if email:
        checkout_data["email"] = email
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": checkout_data,
                "product_options": {"redirect_url": "https://propomi.lat/mi-cuenta?payment=ok"},
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(LEMON_SQUEEZY_STORE_ID)}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }
    req = urllib.request.Request(
        f"{LEMON_SQUEEZY_API_BASE}/checkouts",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {LEMON_SQUEEZY_API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["data"]["attributes"]["url"]
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as exc:
        print(f"[PROPOMI LEMON SQUEEZY] Error checkout: {exc}")
        return None


def _upsert_subscription_from_ls(db: Session, agency_id: str, plan: str, cupo: int | None) -> Subscription:
    now = datetime.now(timezone.utc)
    sub = get_subscription(db, agency_id)
    if sub is None:
        sub = Subscription(
            id=f"sub-{uuid.uuid4().hex[:12]}",
            agency_id=agency_id,
            plan=plan,
            cupo_ciclo=cupo,
            consumido_ciclo=0,
            fecha_renovacion=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
    else:
        sub.plan = plan
        sub.cupo_ciclo = cupo
        sub.consumido_ciclo = 0
        sub.fecha_renovacion = now + timedelta(days=30)
        sub.updated_at = now
    agency = db.get(Agency, agency_id)
    if agency:
        agency.subscription_tier = plan if plan != SubscriptionPlan.PAY_PER_LEAD.value else None
        agency.plan_lead_quota = cupo
        agency.leads_used_current_period = 0
        agency.subscription_started_at = now
        agency.current_period_start = now
    return sub


@app.post("/payments/checkout")
def create_payment_checkout(payload: CheckoutRequestIn, session: dict[str, Any] = Depends(require_agent)):
    """Checkout Lemon: kind=reveal|plan_basic|plan_pro|plan_premium."""
    agency_id = session["agency_id"]
    kind = (payload.kind or "").strip().lower()
    variant_map = {
        "reveal": LEMON_SQUEEZY_VARIANT_ID,
        "plan_basic": LS_VARIANT_PLAN_BASIC,
        "plan_pro": LS_VARIANT_PLAN_PRO,
        "plan_premium": LS_VARIANT_PLAN_PREMIUM,
        "sub_30": LS_VARIANT_PLAN_BASIC,
        "sub_60": LS_VARIANT_PLAN_PRO,
        "sub_unlimited": LS_VARIANT_PLAN_PREMIUM,
    }
    variant_id = variant_map.get(kind)
    if not variant_id:
        raise HTTPException(status_code=400, detail="Plan inválido o variant no configurado")
    if kind == "reveal":
        transaction_id = f"rt-{uuid.uuid4().hex[:12]}"
        with Session(engine) as db:
            db.add(RevealTransaction(
                id=transaction_id, offer_id=payload.offer_id, lead_id=payload.lead_id,
                agency_id=agency_id, method=RevealMethod.PAY_PER_LEAD.value,
                amount_usd=PAY_PER_LEAD_USD, status="PENDING",
            ))
            db.commit()
        custom = {
            "transaction_id": transaction_id, "agency_id": agency_id, "kind": "reveal",
            "offer_id": payload.offer_id or "", "lead_id": payload.lead_id or "",
        }
        url = _ls_create_checkout_url(str(variant_id), agency_id, custom, payload.email)
        if not url:
            raise HTTPException(status_code=502, detail="No se pudo crear el checkout")
        return {"checkout_url": url, "transaction_id": transaction_id}
    custom = {"agency_id": agency_id, "kind": kind}
    url = _ls_create_checkout_url(str(variant_id), agency_id, custom, payload.email)
    if not url:
        raise HTTPException(status_code=502, detail="No se pudo crear el checkout")
    return {"checkout_url": url}


@app.post("/payments/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    """Webhook Lemon Squeezy — firma HMAC obligatoria.
    Eventos: order_created (reveal), subscription_created/updated/cancelled.
    """
    raw_body = await request.body()
    if not LEMON_SQUEEZY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook no configurado (falta LEMON_SQUEEZY_WEBHOOK_SECRET)")
    if not x_signature:
        raise HTTPException(status_code=401, detail="Falta firma")
    expected = hmac.new(LEMON_SQUEEZY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=401, detail="Firma inválida")

    payload = json.loads(raw_body.decode("utf-8"))
    event_name = payload.get("meta", {}).get("event_name")
    custom_data = payload.get("meta", {}).get("custom_data", {}) or {}
    data = payload.get("data") or {}
    attrs = data.get("attributes") or {}

    with Session(engine) as db:
        if event_name == "order_created":
            transaction_id = custom_data.get("transaction_id")
            order_status = attrs.get("status")
            if not transaction_id or order_status != "paid":
                return {"status": "ignored"}
            txn = db.get(RevealTransaction, transaction_id)
            if not txn:
                return {"status": "ignored"}
            if txn.status == "COMPLETED":
                return {"status": "already_completed"}
            now = datetime.now(timezone.utc)
            txn.status = "COMPLETED"
            txn.completed_at = now
            if txn.offer_id:
                offer = db.get(Offer, txn.offer_id)
                if offer and not offer.contact_revealed:
                    offer.contact_revealed = True
                    offer.contact_revealed_at = now
                    db.add(Event(name="contact_revealed", property_id=offer.property_id, user_id=offer.user_id, agency_id=txn.agency_id, context={"method": "pay_per_lead_lemonsqueezy"}))
            if txn.lead_id:
                lead = db.get(Lead, txn.lead_id)
                if lead and not lead.contact_revealed:
                    lead.contact_revealed = True
                    lead.contact_revealed_at = now
            db.commit()
            return {"status": "COMPLETED"}

        if event_name in ("subscription_created", "subscription_updated"):
            agency_id = custom_data.get("agency_id")
            if not agency_id:
                return {"status": "ignored"}
            variant_id = str(
                attrs.get("variant_id")
                or (data.get("relationships") or {}).get("variant", {}).get("data", {}).get("id")
                or ""
            )
            plan_info = _LS_VARIANT_TO_PLAN.get(variant_id)
            if not plan_info:
                kind = (custom_data.get("kind") or "").lower()
                kind_map = {
                    "plan_basic": (SubscriptionPlan.PLAN_30.value, 30),
                    "plan_pro": (SubscriptionPlan.PLAN_50.value, 60),
                    "plan_premium": (SubscriptionPlan.PLAN_99.value, None),
                    "sub_30": (SubscriptionPlan.PLAN_30.value, 30),
                    "sub_60": (SubscriptionPlan.PLAN_50.value, 60),
                    "sub_unlimited": (SubscriptionPlan.PLAN_99.value, None),
                }
                plan_info = kind_map.get(kind)
            if not plan_info:
                return {"status": "ignored"}
            plan, cupo = plan_info
            status = (attrs.get("status") or "active").lower()
            if status in ("cancelled", "expired", "unpaid"):
                sub = get_subscription(db, agency_id)
                if sub:
                    sub.plan = SubscriptionPlan.PAY_PER_LEAD.value
                    sub.cupo_ciclo = 0
                    sub.updated_at = datetime.now(timezone.utc)
                    agency = db.get(Agency, agency_id)
                    if agency:
                        agency.subscription_tier = None
                        agency.plan_lead_quota = 0
                    db.commit()
                return {"status": "subscription_ended"}
            _upsert_subscription_from_ls(db, agency_id, plan, cupo)
            db.commit()
            return {"status": "subscription_upserted"}

        if event_name == "subscription_cancelled":
            agency_id = custom_data.get("agency_id")
            if not agency_id:
                return {"status": "ignored"}
            sub = get_subscription(db, agency_id)
            if sub:
                sub.plan = SubscriptionPlan.PAY_PER_LEAD.value
                sub.cupo_ciclo = 0
                sub.updated_at = datetime.now(timezone.utc)
                agency = db.get(Agency, agency_id)
                if agency:
                    agency.subscription_tier = None
                    agency.plan_lead_quota = 0
                db.commit()
            return {"status": "subscription_cancelled"}

    return {"status": "ignored"}



@app.post("/offers/{offer_id}/{action}")
def offer_action(offer_id: str, action: str, session: dict[str, Any] = Depends(require_agent)):
    if action not in {"accept", "reject", "negotiate"}: raise HTTPException(status_code=400, detail="Acción inválida")
    with Session(engine) as db:
        agency = db.get(Agency, session["agency_id"])
        if not agency or agency.verification_status != "VERIFIED":
            raise HTTPException(status_code=403, detail="Tu agencia todavía no está verificada. No podés gestionar ofertas hasta estar Verificada.")
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


@app.get("/agencies/by-slug/{slug}")
def agency_by_slug(slug: str):
    """Etapa 4 (subdominios por agencia): lookup público, sin auth, para que
    el storefront de una agencia (ej. inmobiliaria-norte.propomi.lat, resuelto
    por un middleware de Next.js que todavía no existe en el frontend) pueda
    traducir el subdominio a un agency_id y después pedir sus propiedades con
    GET /properties?agency_id=<id> (ese endpoint ya es público desde antes).
    Solo expone datos ya públicos en otras pantallas (nombre/ciudad/estado de
    verificación) — nunca teléfono ni ningún dato de contacto."""
    with Session(engine) as db:
        ensure_seed(db)
        ensure_agency_slugs(db)
        a = db.scalars(select(Agency).where(Agency.slug == slug)).first()
        if not a:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        return {"id": a.id, "name": a.name, "city": a.city, "slug": a.slug, "verificationStatus": a.verification_status}


@app.get("/agencies/{agency_id}")
def agency(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        ensure_agency_slugs(db)
        return {
            "id": a.id, "name": a.name, "city": a.city, "verified": a.verified, "claimed": a.claimed, "phone": a.phone,
            "verificationStatus": a.verification_status, "instagram": a.instagram, "websiteLink": a.website_link,
            "freeLeadsRemaining": a.free_leads_remaining, "slug": a.slug,
            "subscriptionTier": a.subscription_tier,
            "planLeadQuota": a.plan_lead_quota,
            "leadsUsedCurrentPeriod": a.leads_used_current_period,
            "subscriptionStartedAt": a.subscription_started_at.isoformat() if a.subscription_started_at else None,
            "availableCredit": get_available_credit(db, a.id),
            "subscription": (lambda s: None if not s else {
                "id": s.id, "agencyId": s.agency_id, "plan": s.plan,
                "cupoCiclo": s.cupo_ciclo, "consumidoCiclo": s.consumido_ciclo,
                "fechaRenovacion": s.fecha_renovacion.isoformat() if s.fecha_renovacion else None,
            })(get_subscription(db, a.id)),
            "leadCredit": (lambda lc: None if not lc else {
                "id": lc.id, "agencyId": lc.agency_id,
                "cupo": lc.cupo, "consumido": lc.consumido,
                "available": max(0, lc.cupo - lc.consumido),
            })(get_lead_credit(db, a.id)),
        }


@app.patch("/agencies/{agency_id}")
def update_agency(agency_id: str, payload: AgencyUpdate, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.name = payload.name.strip()
        if payload.instagram is not None:
            a.instagram = payload.instagram.strip() or None
        if payload.website_link is not None:
            a.website_link = payload.website_link.strip() or None
        db.commit()
        return {"id": a.id, "name": a.name, "verified": a.verified, "verificationStatus": a.verification_status, "instagram": a.instagram, "websiteLink": a.website_link}


@app.post("/agencies/{agency_id}/subscription")
def set_agency_subscription(agency_id: str, payload: SubscriptionIn, session: dict[str, Any] = Depends(require_agent)):
    """Crea o cambia el plan activo. Sin pasarela real. Solo VERIFIED."""
    if session["agency_id"] != agency_id:
        raise HTTPException(status_code=403, detail="Agencia no autorizada")
    plan = (payload.plan or "").strip().upper()
    if plan not in PLAN_CUPO:
        raise HTTPException(status_code=400, detail=f"Plan inválido. Valores: {', '.join(PLAN_CUPO.keys())}")
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        if a.verification_status != "VERIFIED":
            raise HTTPException(status_code=403, detail="Solo agencias verificadas pueden registrar o cambiar de plan.")
        now = datetime.now(timezone.utc)
        cupo = PLAN_CUPO[plan]
        sub = get_subscription(db, agency_id)
        if sub is None:
            sub = Subscription(
                id=f"sub-{uuid.uuid4().hex[:12]}", agency_id=agency_id, plan=plan,
                cupo_ciclo=cupo, consumido_ciclo=0, fecha_renovacion=now + timedelta(days=30),
                created_at=now, updated_at=now,
            )
            db.add(sub)
        else:
            sub.plan = plan
            sub.cupo_ciclo = cupo
            sub.consumido_ciclo = 0
            sub.fecha_renovacion = now + timedelta(days=30)
            sub.updated_at = now
        a.subscription_tier = plan if plan != SubscriptionPlan.PAY_PER_LEAD.value else None
        a.plan_lead_quota = cupo
        a.leads_used_current_period = 0
        a.subscription_started_at = now
        a.current_period_start = now
        db.commit()
        return {
            "id": sub.id, "agencyId": sub.agency_id, "plan": sub.plan,
            "cupoCiclo": sub.cupo_ciclo, "consumidoCiclo": sub.consumido_ciclo,
            "fechaRenovacion": sub.fecha_renovacion.isoformat() if sub.fecha_renovacion else None,
            "availableCredit": get_available_credit(db, agency_id),
        }


@app.post("/agencies/{agency_id}/relink-by-phone")
def relink_by_phone(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        count = sum(relink_properties(db, agency_id, phone) for phone in all_agency_phones(db, agency_id))
        db.commit()
        props = db.scalars(select(Property).where(Property.agency_id == agency_id)).all()
        return {"count": count, "properties": [prop_dict(p) for p in props], "message": f"Encontramos {count} publicaciones nuevas vinculadas por teléfono." if count else "No encontramos publicaciones nuevas con ese teléfono."}


@app.get("/agencies/{agency_id}/phones")
def list_agency_phones(agency_id: str, session: dict[str, Any] = Depends(require_agent)):
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    with Session(engine) as db:
        agency = db.get(Agency, agency_id)
        if not agency: raise HTTPException(status_code=404, detail="Agencia no encontrada")
        extras = db.scalars(select(AgencyPhone).where(AgencyPhone.agency_id == agency_id)).all()
        return {
            "primary": agency.phone,
            "extras": [{"id": ap.id, "phone": ap.phone, "verified": ap.verified_at is not None, "created_at": ap.created_at.isoformat()} for ap in extras],
        }


@app.post("/agencies/{agency_id}/phones")
def add_agency_phone(agency_id: str, payload: PhoneIn, session: dict[str, Any] = Depends(require_agent)):
    """Suma un telefono adicional (celular personal, linea de oficina) a una agencia ya autenticada.
    No requiere OTP propio en esta version: el telefono principal de la agencia ya paso por OTP
    al loguearse, y agregar un numero mas queda auditado via created_at (verified_at se completa
    cuando en una etapa futura se conecte una verificacion por OTP tambien sobre este numero)."""
    if session["agency_id"] != agency_id: raise HTTPException(status_code=403, detail="Agencia no autorizada")
    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Ingresá un teléfono válido")
    with Session(engine) as db:
        if not db.get(Agency, agency_id):
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        if find_agency_by_phone(db, phone):
            raise HTTPException(status_code=409, detail="Ese teléfono ya está asociado a una agencia")
        ap = AgencyPhone(id=f"aph-{uuid.uuid4().hex[:12]}", agency_id=agency_id, phone=phone)
        db.add(ap)
        db.commit()
        return {"id": ap.id, "phone": ap.phone, "verified": False}


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


class SearchPerformedIn(BaseModel):
    """Filtros anónimos de búsqueda — sin PII."""
    model_config = {"extra": "forbid"}

    zone: str | None = None
    precio_min: float | None = None
    precio_max: float | None = None
    tipo: str | None = None
    ambientes: int | None = None
    type: str | None = None
    rooms: int | None = None
    max_price: float | None = None
    min_price: float | None = None


_PII_KEY_HINTS = ("phone", "telefono", "teléfono", "email", "mail", "nombre", "name", "dni", "buyer_")


@app.post("/events/search_performed", status_code=201)
async def post_search_performed(request: Request):
    """Registra búsqueda agregada anónima. Rechaza campos que parezcan PII."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body debe ser objeto")
    for k in body.keys():
        kl = str(k).lower()
        if any(h in kl for h in _PII_KEY_HINTS):
            raise HTTPException(status_code=400, detail=f"Campo no permitido (PII): {k}")
    try:
        payload = SearchPerformedIn(**body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Filtros inválidos: {exc}") from exc
    zone = payload.zone
    tipo = payload.tipo or payload.type
    ambientes = payload.ambientes if payload.ambientes is not None else payload.rooms
    precio_max = payload.precio_max if payload.precio_max is not None else payload.max_price
    precio_min = payload.precio_min if payload.precio_min is not None else payload.min_price
    filters = {k: v for k, v in {
        "zone": zone, "type": tipo, "rooms": ambientes,
        "min_price": precio_min, "max_price": precio_max,
    }.items() if v is not None}
    with Session(engine) as db:
        db.add(Event(
            name="search_performed",
            session_id=request.headers.get("x-session-id"),
            context={"filters": filters, "source": "explicit"},
        ))
        db.commit()
    return {"ok": True}


@app.get("/analytics/demand")
def demand(limit: int = 500, session: dict[str, Any] = Depends(require_agent)):
    """Etapa 3 (sección 10 / fase Intelligence): lee los eventos
    `search_performed` que ya se vienen guardando desde GET /properties y
    los agrega en rankings simples de demanda (zonas y tipos más buscados).
    No hay tabla propia de agregación todavía — se calcula al vuelo sobre
    los últimos `limit` eventos (default 500) para no recorrer toda la
    tabla en cada llamada a medida que crezca. Es agregado y anónimo: nunca
    devuelve user_id ni ningún dato de una búsqueda individual, solo
    conteos totales por valor de filtro.
    """
    with Session(engine) as db:
        events = db.scalars(
            select(Event)
            .where(Event.name == "search_performed")
            .order_by(Event.created_at.desc())
            .limit(limit)
        ).all()
        zone_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        operation_counts: dict[str, int] = {}
        result_counts_sum = 0
        result_counts_n = 0
        for e in events:
            filters = (e.context or {}).get("filters", {})
            zone = filters.get("zone")
            if zone:
                zone_counts[zone] = zone_counts.get(zone, 0) + 1
            prop_type = filters.get("type")
            if prop_type:
                type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
            operation = filters.get("operation")
            if operation:
                operation_counts[operation] = operation_counts.get(operation, 0) + 1
            result_count = (e.context or {}).get("result_count")
            if isinstance(result_count, (int, float)):
                result_counts_sum += result_count
                result_counts_n += 1
        top_zones = sorted(zone_counts.items(), key=lambda kv: kv[1], reverse=True)
        top_types = sorted(type_counts.items(), key=lambda kv: kv[1], reverse=True)
        top_operations = sorted(operation_counts.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "sampleSize": len(events),
            "topZones": [{"zone": z, "count": c} for z, c in top_zones],
            "topTypes": [{"type": t, "count": c} for t, c in top_types],
            "topOperations": [{"operation": o, "count": c} for o, c in top_operations],
            "avgResultCount": (result_counts_sum / result_counts_n) if result_counts_n else None,
        }




@app.get("/agencies/{agency_id}/market-opportunities")
def market_opportunities(
    agency_id: str,
    days: int = 30,
    limit: int = 1000,
    session: dict[str, Any] = Depends(require_agent),
):
    """T5.7: cruza search_performed agregados (zona, max_price, type, rooms)
    contra las zonas donde ESTA agencia tiene catálogo. Solo VERIFIED.
    Agregado y anónimo: nunca user_id ni búsquedas individuales."""
    if session["agency_id"] != agency_id:
        raise HTTPException(status_code=403, detail="Agencia no autorizada")
    days = max(1, min(days, 90))
    limit = max(1, min(limit, 5000))
    with Session(engine) as db:
        agency = db.get(Agency, agency_id)
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        if agency.verification_status != "VERIFIED":
            raise HTTPException(
                status_code=403,
                detail="Tu agencia todavía no está verificada. Las oportunidades de mercado solo están disponibles para cuentas Verificadas.",
            )

        props = db.scalars(select(Property).where(Property.agency_id == agency_id)).all()
        # Zonas del catálogo de la agencia (solo esas — no mostrar demanda de zonas que no vende)
        agency_zones: dict[str, int] = {}
        for p in props:
            if p.zone:
                agency_zones[p.zone] = agency_zones.get(p.zone, 0) + 1
        if not agency_zones:
            return {"days": days, "sampleSize": 0, "zones": []}

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = db.scalars(
            select(Event)
            .where(Event.name == "search_performed")
            .order_by(Event.created_at.desc())
            .limit(limit)
        ).all()

        # Por zona de la agencia: conteo de búsquedas + max_price observados
        zone_stats: dict[str, dict[str, Any]] = {
            z: {"searchCount": 0, "maxPrices": [], "types": {}, "rooms": {}}
            for z in agency_zones
        }
        sample = 0
        for e in events:
            created = e.created_at
            if created is not None:
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    continue
            filters = (e.context or {}).get("filters", {}) or {}
            zone = filters.get("zone")
            if not zone or zone not in zone_stats:
                continue
            sample += 1
            zone_stats[zone]["searchCount"] += 1
            mp = filters.get("max_price")
            if isinstance(mp, (int, float)) and mp > 0:
                zone_stats[zone]["maxPrices"].append(float(mp))
            t = filters.get("type")
            if t:
                zone_stats[zone]["types"][t] = zone_stats[zone]["types"].get(t, 0) + 1
            r = filters.get("rooms")
            if r is not None:
                key = str(r)
                zone_stats[zone]["rooms"][key] = zone_stats[zone]["rooms"].get(key, 0) + 1

        rows = []
        for zone, st in zone_stats.items():
            prices = sorted(st["maxPrices"])
            budget_min = prices[0] if prices else None
            budget_max = prices[-1] if prices else None
            # rango más buscado: mediana simple de max_price
            budget_median = None
            if prices:
                mid = len(prices) // 2
                budget_median = prices[mid] if len(prices) % 2 == 1 else (prices[mid - 1] + prices[mid]) / 2
            top_type = None
            if st["types"]:
                top_type = max(st["types"].items(), key=lambda kv: kv[1])[0]
            top_rooms = None
            if st["rooms"]:
                top_rooms = max(st["rooms"].items(), key=lambda kv: kv[1])[0]
            rows.append({
                "zone": zone,
                "agencyListingCount": agency_zones[zone],
                "searchCount": st["searchCount"],
                "budgetMin": budget_min,
                "budgetMax": budget_max,
                "budgetMedian": budget_median,
                "topType": top_type,
                "topRooms": top_rooms,
            })
        rows.sort(key=lambda r: r["searchCount"], reverse=True)
        return {
            "days": days,
            "sampleSize": sample,
            "zones": rows,
        }


class AgencyReviewIn(BaseModel):
    notes: str | None = None


def agency_admin_dict(a: "Agency") -> dict[str, Any]:
    return {
        "id": a.id, "name": a.name, "city": a.city, "phone": a.phone, "claimed": a.claimed,
        "instagram": a.instagram, "websiteLink": a.website_link,
        "verificationStatus": a.verification_status, "verificationPriority": a.verification_priority,
        "verificationNotes": a.verification_notes,
        "verificationReviewedAt": a.verification_reviewed_at.isoformat() if a.verification_reviewed_at else None,
    }


@app.get("/admin/agencies/pending")
def admin_pending_agencies(_: None = Depends(require_admin)):
    """Etapa 4: cola de agencias pendientes de revisión manual, ordenada
    por `verification_priority` descendente (doc 6.2 — quien ya se
    suscribió antes de verificarse pasa primero, SLA 24hs)."""
    with Session(engine) as db:
        ensure_seed(db)
        rows = db.scalars(
            select(Agency)
            .where(Agency.verification_status == "PENDING")
            .order_by(Agency.verification_priority.desc(), Agency.id)
        ).all()
        return [agency_admin_dict(a) for a in rows]


@app.post("/admin/agencies/{agency_id}/approve")
def admin_approve_agency(agency_id: str, payload: AgencyReviewIn | None = None, _: None = Depends(require_admin)):
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.verification_status = "VERIFIED"
        a.verified = True  # DEPRECATED, se mantiene en sync por compatibilidad hacia atrás
        a.verification_reviewed_at = datetime.now(timezone.utc)
        if payload and payload.notes:
            a.verification_notes = sanitize_free_text(payload.notes, "notas de revisión")
        # Los 10 leads gratis al verificarse (doc 06.2.3/08) se otorgan acá,
        # una sola vez — si por algún motivo ya tenía cupo cargado (no
        # debería pasar en el flujo normal), no se lo pisa ni se lo duplica.
        if a.free_leads_remaining == 0:
            a.free_leads_remaining = FREE_LEADS_ON_VERIFICATION
        lc = get_lead_credit(db, a.id)
        if lc is None:
            db.add(LeadCredit(id=f"lc-{uuid.uuid4().hex[:12]}", agency_id=a.id, cupo=FREE_LEADS_ON_VERIFICATION, consumido=0))
        elif (lc.cupo - lc.consumido) == 0 and a.free_leads_remaining > 0:
            lc.cupo = a.free_leads_remaining
            lc.consumido = 0
            lc.updated_at = datetime.now(timezone.utc)
        db.commit()
        return agency_admin_dict(a)


@app.post("/admin/agencies/{agency_id}/reject")
def admin_reject_agency(agency_id: str, payload: AgencyReviewIn | None = None, _: None = Depends(require_admin)):
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.verification_status = "REJECTED"
        a.verified = False
        a.verification_reviewed_at = datetime.now(timezone.utc)
        if payload and payload.notes:
            a.verification_notes = sanitize_free_text(payload.notes, "notas de revisión")
        db.commit()
        return agency_admin_dict(a)




@app.post("/admin/agencies/{agency_id}/reopen")
def admin_reopen_agency(agency_id: str, payload: AgencyReviewIn | None = None, _: None = Depends(require_admin)):
    """Soporte: vuelve una agencia REJECTED (o VERIFIED, si hace falta re-revisar)
    a PENDING sin inventar leads gratis de nuevo."""
    with Session(engine) as db:
        a = db.get(Agency, agency_id)
        if not a:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        a.verification_status = "PENDING"
        a.verified = False
        a.verification_reviewed_at = None
        if payload and payload.notes:
            a.verification_notes = sanitize_free_text(payload.notes, "notas de revisión")
        db.commit()
        return agency_admin_dict(a)


@app.get("/admin/agencies")
def admin_list_agencies(
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
    _: None = Depends(require_admin),
):
    """Listado de soporte: todas las agencias (o filtradas por status / texto).
    No expone datos de compradores — solo perfil de agencia."""
    limit = max(1, min(limit, 500))
    with Session(engine) as db:
        ensure_seed(db)
        stmt = select(Agency)
        if status:
            st = status.strip().upper()
            if st not in {"PENDING", "VERIFIED", "REJECTED"}:
                raise HTTPException(status_code=400, detail="status inválido")
            stmt = stmt.where(Agency.verification_status == st)
        rows = list(db.scalars(stmt.order_by(Agency.name)).all())
        if q:
            needle = q.strip().lower()
            def match(a: Agency) -> bool:
                blob = " ".join([
                    a.id or "", a.name or "", a.city or "", a.phone or "",
                    a.instagram or "", a.slug or "", a.website_link or "",
                ]).lower()
                return needle in blob
            rows = [a for a in rows if match(a)]
        return {
            "count": len(rows[:limit]),
            "totalMatched": len(rows),
            "items": [agency_admin_dict(a) for a in rows[:limit]],
        }


@app.get("/admin/cold-start/pending")
def admin_cold_start_pending(_: None = Depends(require_admin)):
    """Cola de notificaciones manuales T6.1. Único endpoint que expone el
    teléfono scrapeado de la agencia no reclamada — protegido por X-Admin-Key.
    El resumen de la oferta nunca incluye datos del comprador."""
    with Session(engine) as db:
        tasks = db.scalars(
            select(ColdStartTask)
            .where(ColdStartTask.status == "PENDING")
            .order_by(ColdStartTask.created_at.asc())
        ).all()
        return [
            {
                "id": t.id,
                "offerId": t.offer_id,
                "propertyId": t.property_id,
                "agencyId": t.agency_id,
                "targetPhone": t.target_phone,
                "amount": t.amount,
                "currency": t.currency,
                "propertyTitle": t.property_title,
                "propertyZone": t.property_zone,
                "onboardingToken": t.onboarding_token,
                "onboardingPath": f"/onboarding/{t.onboarding_token}",
                "status": t.status,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
                "messageTemplate": (
                    f"Hola — alguien ofreció {t.currency} {t.amount:,.0f} por "
                    f"«{t.property_title}» ({t.property_zone}) en Propomi. "
                    f"Reclamá tu perfil y ver el detalle: "
                    f"https://propomi.lat/onboarding/{t.onboarding_token}"
                ),
            }
            for t in tasks
        ]


class ColdStartMarkIn(BaseModel):
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def check_notes(cls, v: str | None) -> str | None:
        return sanitize_free_text(v, campo="notes")


@app.post("/admin/cold-start/{task_id}/mark-sent")
def admin_cold_start_mark_sent(
    task_id: str,
    payload: ColdStartMarkIn | None = None,
    _: None = Depends(require_admin),
):
    with Session(engine) as db:
        task = db.get(ColdStartTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        if task.status not in {"PENDING", "SENT"}:
            raise HTTPException(status_code=400, detail=f"Estado actual: {task.status}")
        task.status = "SENT"
        task.sent_at = datetime.now(timezone.utc)
        if payload and payload.notes:
            task.notes = payload.notes
        db.commit()
        return {"id": task.id, "status": task.status, "sentAt": task.sent_at.isoformat()}


@app.get("/onboarding/{token}")
def get_onboarding(token: str):
    """T6.2: resumen público del cold-start. Nunca expone teléfonos ni
    datos del comprador — solo lo necesario para motivar el claim."""
    with Session(engine) as db:
        task = db.scalar(select(ColdStartTask).where(ColdStartTask.onboarding_token == token))
        if not task:
            raise HTTPException(status_code=404, detail="Link inválido o vencido")
        created = task.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and datetime.now(timezone.utc) - created > timedelta(days=ONBOARDING_TOKEN_DAYS):
            if task.status in {"PENDING", "SENT"}:
                task.status = "EXPIRED"
                db.commit()
            raise HTTPException(status_code=410, detail="Este link de onboarding expiró")
        if task.status == "CLAIMED":
            return {
                "status": "CLAIMED",
                "propertyTitle": task.property_title,
                "propertyZone": task.property_zone,
                "amount": task.amount,
                "currency": task.currency,
                "message": "Este perfil ya fue reclamado. Entrá a /agencia con tu teléfono.",
            }
        if task.status == "EXPIRED":
            raise HTTPException(status_code=410, detail="Este link de onboarding expiró")
        agency_name = None
        if task.agency_id:
            agency = db.get(Agency, task.agency_id)
            agency_name = agency.name if agency else None
        return {
            "status": task.status,
            "propertyTitle": task.property_title,
            "propertyZone": task.property_zone,
            "amount": task.amount,
            "currency": task.currency,
            "agencyId": task.agency_id,
            "agencyName": agency_name,
            "expiresInDays": ONBOARDING_TOKEN_DAYS,
        }


class OnboardingCompleteIn(BaseModel):
    instagram: str = Field(min_length=2, max_length=120)
    website_link: str | None = Field(default=None, max_length=300)
    name: str | None = Field(default=None, max_length=180)


@app.post("/onboarding/{token}/complete")
def complete_onboarding(
    token: str,
    payload: OnboardingCompleteIn,
    session: dict[str, Any] = Depends(require_agent),
):
    """T6.2: el agente (ya autenticado por OTP con el teléfono de la
    agencia) completa Instagram/link, marca claimed y consume el token.
    Token de un solo uso: status → CLAIMED."""
    with Session(engine) as db:
        task = db.scalar(select(ColdStartTask).where(ColdStartTask.onboarding_token == token))
        if not task:
            raise HTTPException(status_code=404, detail="Link inválido o vencido")
        created = task.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and datetime.now(timezone.utc) - created > timedelta(days=ONBOARDING_TOKEN_DAYS):
            task.status = "EXPIRED"
            db.commit()
            raise HTTPException(status_code=410, detail="Este link de onboarding expiró")
        if task.status == "CLAIMED":
            raise HTTPException(status_code=400, detail="Este perfil ya fue reclamado")
        if task.status == "EXPIRED":
            raise HTTPException(status_code=410, detail="Este link de onboarding expiró")
        if not task.agency_id:
            raise HTTPException(status_code=400, detail="Esta invitación no tiene agencia asociada todavía")
        if session.get("agency_id") != task.agency_id:
            raise HTTPException(
                status_code=403,
                detail="Entrá con el teléfono de la agencia asociada a esta invitación.",
            )
        agency = db.get(Agency, task.agency_id)
        if not agency:
            raise HTTPException(status_code=404, detail="Agencia no encontrada")
        agency.claimed = True
        agency.instagram = payload.instagram.strip() or None
        if payload.website_link is not None:
            agency.website_link = payload.website_link.strip() or None
        if payload.name and payload.name.strip():
            agency.name = payload.name.strip()
        # Si sigue PENDING de verificación, queda en cola; no auto-VERIFIED.
        if agency.verification_status not in {"VERIFIED", "REJECTED"}:
            agency.verification_status = "PENDING"
        task.status = "CLAIMED"
        db.commit()
        return {
            "status": "CLAIMED",
            "agencyId": agency.id,
            "agencyName": agency.name,
            "verificationStatus": agency.verification_status,
            "message": "Perfil reclamado. Completá la verificación desde el panel de agencia si todavía está pendiente.",
        }



@app.post("/admin/crawler/run")
def admin_run_crawler(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    sources: str | None = None,
):
    """Disparo manual del crawler (protegido por ADMIN_KEY). sources=zonaprop,argenprop"""
    if not x_admin_key or not secrets.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(status_code=401, detail="Admin key inválida")
    from .crawler import run_crawl
    source_ids = [s.strip() for s in (sources or "").split(",") if s.strip()] or None
    with Session(engine) as db:
        report = run_crawl(db, source_ids)
    return report
