"""Vonage Messages API — transporte de OTP por WhatsApp.

A diferencia de sms_vonage.py (Vonage SMS API classic, auth simple con
api_key+api_secret), la Messages API que maneja WhatsApp se autentica con un
JWT firmado (RS256) usando la clave privada que Vonage entrega al crear una
"Application" en el dashboard (Developer API Settings → Applications →
Generate public/private key pair, con capability "Messages" habilitada y
linkeada al número de WhatsApp Business).

Requisito externo obligatorio (no resuelve este archivo):
- Meta exige una PLANTILLA PRE-APROBADA para cualquier mensaje que la
  empresa inicia primero (un OTP es exactamente eso — el usuario no le
  escribió antes al número). Sin plantilla aprobada, Meta rechaza el envío
  fuera de una ventana de sesión de 24hs. La aprobación de plantilla la
  hace Meta, no Vonage, y tarda de horas a un par de días.
- Mientras no haya plantilla aprobada, se puede probar en modo texto plano
  (WHATSAPP_MESSAGE_MODE=text) SOLO contra el WhatsApp Sandbox de Vonage
  (números de prueba que vos mismo agregás), nunca contra un cliente real.

Variables de entorno:
  VONAGE_APPLICATION_ID       — id de la Application (dashboard Vonage)
  VONAGE_PRIVATE_KEY          — contenido del private.key (PEM), como string
  VONAGE_WHATSAPP_FROM        — número de WhatsApp Business (o sandbox), sin '+'
  WHATSAPP_MESSAGE_MODE       — "text" (sandbox/pruebas) | "template" (producción)
  WHATSAPP_TEMPLATE_NAME      — nombre exacto de la plantilla aprobada en Meta
  WHATSAPP_TEMPLATE_LOCALE    — default "es_AR"
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

import jwt
import requests

VONAGE_APPLICATION_ID = os.getenv("VONAGE_APPLICATION_ID", "")
VONAGE_PRIVATE_KEY = os.getenv("VONAGE_PRIVATE_KEY", "")
VONAGE_WHATSAPP_FROM = os.getenv("VONAGE_WHATSAPP_FROM", "")
WHATSAPP_MESSAGE_MODE = os.getenv("WHATSAPP_MESSAGE_MODE", "text").strip().lower()
WHATSAPP_TEMPLATE_NAME = os.getenv("WHATSAPP_TEMPLATE_NAME", "")
WHATSAPP_TEMPLATE_LOCALE = os.getenv("WHATSAPP_TEMPLATE_LOCALE", "es_AR")
VONAGE_MESSAGES_URL = "https://api.nexmo.com/v1/messages"


class VonageWhatsappError(Exception):
    pass


def _build_jwt() -> str:
    if not VONAGE_APPLICATION_ID or not VONAGE_PRIVATE_KEY:
        raise VonageWhatsappError(
            "Falta VONAGE_APPLICATION_ID o VONAGE_PRIVATE_KEY (WhatsApp usa "
            "una Application de Vonage, distinta de las credenciales de SMS)."
        )
    now = int(time.time())
    claims = {
        "iat": now,
        "exp": now + 60,
        "jti": uuid.uuid4().hex,
        "application_id": VONAGE_APPLICATION_ID,
    }
    return jwt.encode(claims, VONAGE_PRIVATE_KEY, algorithm="RS256")


def send_otp_whatsapp(to_e164: str, code: str) -> dict[str, Any]:
    """Envía el código OTP por WhatsApp vía Vonage Messages API.

    En modo "text": mensaje libre — solo válido en Sandbox o dentro de una
    sesión de 24hs ya abierta por el usuario. Meta lo rechaza si no.
    En modo "template": usa una plantilla aprobada (obligatorio en
    producción para mensajes que inicia la empresa, como un OTP).
    """
    if not VONAGE_WHATSAPP_FROM:
        raise VonageWhatsappError("Falta VONAGE_WHATSAPP_FROM (número de WhatsApp Business/Sandbox).")

    to_clean = to_e164.lstrip("+").replace(" ", "")
    token = _build_jwt()

    if WHATSAPP_MESSAGE_MODE == "template":
        if not WHATSAPP_TEMPLATE_NAME:
            raise VonageWhatsappError(
                "WHATSAPP_MESSAGE_MODE=template pero falta WHATSAPP_TEMPLATE_NAME "
                "(nombre exacto de la plantilla aprobada por Meta)."
            )
        payload: dict[str, Any] = {
            "message_type": "template",
            "template": {
                "name": WHATSAPP_TEMPLATE_NAME,
                "parameters": [code],
            },
            "whatsapp": {"policy": "deterministic", "locale": WHATSAPP_TEMPLATE_LOCALE},
            "to": to_clean,
            "from": VONAGE_WHATSAPP_FROM,
            "channel": "whatsapp",
        }
    else:
        payload = {
            "message_type": "text",
            "text": f"Tu código Propomi es {code}. Vence en 10 minutos. No lo compartas.",
            "to": to_clean,
            "from": VONAGE_WHATSAPP_FROM,
            "channel": "whatsapp",
        }

    try:
        resp = requests.post(
            VONAGE_MESSAGES_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise VonageWhatsappError(f"Error de red hacia Vonage Messages API: {exc}") from exc

    if resp.status_code >= 300:
        raise VonageWhatsappError(f"Vonage HTTP {resp.status_code}: {resp.text}")

    return resp.json()
