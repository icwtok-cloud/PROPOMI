"""WhatsApp Cloud API (Meta Graph) — transporte de OTP.

Canal oficial de Meta (graph.facebook.com), sin Vonage. Reemplazo previsto
cuando Vonage rechaza el método de pago: se activa con
OTP_SMS_PROVIDER=whatsapp_cloud y las credenciales de la app Meta / número
de WhatsApp Business Cloud.

Requisito externo obligatorio (no resuelve este archivo):
- Meta exige una PLANTILLA PRE-APROBADA para cualquier mensaje que la
  empresa inicia primero (un OTP es exactamente eso — el usuario no le
  escribió antes al número). Sin plantilla aprobada, Meta rechaza el envío
  fuera de una ventana de sesión de 24hs. La aprobación de plantilla la
  hace Meta en el Manager de WhatsApp Business y tarda de horas a un par
  de días.
- Mientras no haya plantilla aprobada (WHATSAPP_CLOUD_TEMPLATE_NAME vacío),
  se puede probar en modo texto plano SOLO dentro de una sesión de 24hs ya
  abierta por el usuario (él escribió primero al número de negocio). Nunca
  contra un cliente frío en producción.

Variables de entorno:
  WHATSAPP_CLOUD_TOKEN            — access token permanente (o de sistema)
  WHATSAPP_CLOUD_PHONE_NUMBER_ID  — id del número en Graph (no el MSISDN)
  WHATSAPP_CLOUD_TEMPLATE_NAME    — nombre exacto de la plantilla aprobada
  WHATSAPP_CLOUD_TEMPLATE_LOCALE  — default "es_AR"
  WHATSAPP_CLOUD_API_VERSION      — default "v21.0"
  WHATSAPP_CLOUD_KEEP_AR_NINE     — default false; si true no saca el "9" de móviles AR
"""
from __future__ import annotations

import os
from typing import Any

import requests

WHATSAPP_CLOUD_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
WHATSAPP_CLOUD_PHONE_NUMBER_ID = os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID", "")
WHATSAPP_CLOUD_TEMPLATE_NAME = os.getenv("WHATSAPP_CLOUD_TEMPLATE_NAME", "")
WHATSAPP_CLOUD_TEMPLATE_LOCALE = os.getenv("WHATSAPP_CLOUD_TEMPLATE_LOCALE", "es_AR")
WHATSAPP_CLOUD_API_VERSION = os.getenv("WHATSAPP_CLOUD_API_VERSION", "v21.0")
# Mismo patrón que VONAGE_KEEP_AR_NINE (sms_vonage.py). Meta Graph API en modo
# de prueba matchea el destinatario del allowed list tal cual se registró
# (a menudo sin el "9" de móviles AR E.164). Default false = sacar el "9"
# post-54 al enviar. Poner true solo si el número de prueba en Meta quedó
# cargado CON el "9".
WHATSAPP_CLOUD_KEEP_AR_NINE = os.getenv("WHATSAPP_CLOUD_KEEP_AR_NINE", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)


class WhatsappCloudError(Exception):
    pass


def send_otp_whatsapp_cloud(to_e164: str, code: str) -> dict[str, Any]:
    """Envía el código OTP por WhatsApp Cloud API (Meta Graph).

    Si WHATSAPP_CLOUD_TEMPLATE_NAME está seteado → mensaje tipo "template"
    (obligatorio en producción para mensajes iniciados por la empresa).
    Si no → fallback texto plano (solo válido dentro de una sesión de 24hs
    ya abierta por el usuario).
    """
    if not WHATSAPP_CLOUD_TOKEN or not WHATSAPP_CLOUD_PHONE_NUMBER_ID:
        raise WhatsappCloudError(
            "Falta WHATSAPP_CLOUD_TOKEN o WHATSAPP_CLOUD_PHONE_NUMBER_ID "
            "(credenciales de WhatsApp Cloud API / Meta Graph)."
        )

    to_clean = to_e164.lstrip("+").replace(" ", "")
    if to_clean.startswith("549") and not WHATSAPP_CLOUD_KEEP_AR_NINE:
        # Meta Graph API rechaza (#131030 Recipient phone number not in
        # allowed list) los móviles argentinos cuando el allowed list de
        # prueba se cargó sin el "9" de E.164 y el envío va CON el "9".
        # Confirmado en prod: mismo número, con "9" -> 131030; sin "9" ->
        # entregado. Solo afecta el payload a Graph; el resto de la app
        # sigue usando el E.164 completo con "9".
        # EXCEPCIÓN: con WHATSAPP_CLOUD_KEEP_AR_NINE=true no se saca el "9",
        # si el destinatario de prueba en Meta se registró con el "9".
        to_clean = "54" + to_clean[3:]
    url = (
        f"https://graph.facebook.com/{WHATSAPP_CLOUD_API_VERSION}/"
        f"{WHATSAPP_CLOUD_PHONE_NUMBER_ID}/messages"
    )

    if WHATSAPP_CLOUD_TEMPLATE_NAME:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": "template",
            "template": {
                "name": WHATSAPP_CLOUD_TEMPLATE_NAME,
                "language": {"code": WHATSAPP_CLOUD_TEMPLATE_LOCALE},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": code}],
                    }
                ],
            },
        }
    else:
        # Texto plano: Meta solo lo acepta dentro de ventana de 24hs abierta
        # por el usuario. En producción usar plantilla aprobada.
        payload = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": "text",
            "text": {
                "body": (
                    f"Tu código Propomi es {code}. "
                    "Vence en 10 minutos. No lo compartas."
                ),
            },
        }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {WHATSAPP_CLOUD_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise WhatsappCloudError(f"Error de red hacia WhatsApp Cloud API: {exc}") from exc

    if resp.status_code >= 300:
        raise WhatsappCloudError(f"WhatsApp Cloud HTTP {resp.status_code}: {resp.text}")

    return resp.json()
