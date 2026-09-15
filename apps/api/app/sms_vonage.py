"""Vonage SMS API classic — transporte de OTP.

No usa Verify API ni Messages API: el repo genera/valida el código (hash, TTL,
intentos). Solo envía el SMS vía POST https://rest.nexmo.com/sms/json.

Credenciales: VONAGE_API_KEY + VONAGE_API_SECRET.
Remitente: VONAGE_SMS_FROM (default "Propomi").
"""
from __future__ import annotations

import os
from typing import Any

import requests

VONAGE_API_KEY = os.getenv("VONAGE_API_KEY", "")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET", "")
VONAGE_SMS_FROM = os.getenv("VONAGE_SMS_FROM", "Propomi")
VONAGE_SMS_URL = "https://rest.nexmo.com/sms/json"


class VonageSMSError(Exception):
    pass


def send_otp_sms(to_e164: str, code: str) -> dict[str, Any]:
    """Envía el código OTP por SMS vía Vonage SMS API classic.

    to_e164: número E.164 (con o sin '+'); se envían solo dígitos.
    Devuelve el JSON de respuesta de Vonage.
    Lanza VonageSMSError si faltan credenciales o status != 0.
    """
    if not VONAGE_API_KEY or not VONAGE_API_SECRET:
        raise VonageSMSError("Vonage no está configurado (faltan VONAGE_API_KEY / VONAGE_API_SECRET)")

    to_clean = to_e164.lstrip("+").replace(" ", "")
    if to_clean.startswith("549"):
        # Vonage rechaza (AR-UNKNOWN / status "rejected") los móviles argentinos
        # cuando se les manda el "9" de E.164. Confirmado en el dashboard de
        # Vonage: mismo número, con "9" -> rejected; sin "9" -> delivered.
        # Solo afecta el envío a Vonage; el resto de la app sigue usando el
        # E.164 completo con "9" (normalize_phone, DB, rate-limit, etc.).
        to_clean = "54" + to_clean[3:]
    payload = {
        "api_key": VONAGE_API_KEY,
        "api_secret": VONAGE_API_SECRET,
        "from": VONAGE_SMS_FROM,
        "to": to_clean,
        "text": f"Tu código Propomi es {code}. Vence en 10 minutos. No lo compartas.",
    }
    try:
        resp = requests.post(VONAGE_SMS_URL, data=payload, timeout=10)
    except requests.RequestException as exc:
        raise VonageSMSError(f"Error de red hacia Vonage: {exc}") from exc

    if resp.status_code >= 300:
        raise VonageSMSError(f"Vonage HTTP {resp.status_code}: {resp.text}")

    body = resp.json()
    messages = body.get("messages") or []
    if not messages:
        raise VonageSMSError(f"Vonage sin messages en respuesta: {body}")
    status = str(messages[0].get("status", ""))
    if status != "0":
        err = messages[0].get("error-text") or messages[0].get("error_text") or body
        raise VonageSMSError(f"Vonage status={status}: {err}")
    return body
