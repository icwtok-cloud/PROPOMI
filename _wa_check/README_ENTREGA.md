# Entrega: OTP vía WhatsApp Cloud API (Meta)

**Base:** `main` @ `3cc01be`  
**Fecha:** 2026-09-17

## Cambio

1. **Nuevo** `apps/api/app/whatsapp_cloud.py`
   - `send_otp_whatsapp_cloud(to_e164, code)` → Graph API
   - Plantilla si `WHATSAPP_CLOUD_TEMPLATE_NAME` (producción)
   - Texto plano si no (solo sesión 24hs)
   - Env: `WHATSAPP_CLOUD_TOKEN`, `WHATSAPP_CLOUD_PHONE_NUMBER_ID`,
     `WHATSAPP_CLOUD_TEMPLATE_NAME`, `WHATSAPP_CLOUD_TEMPLATE_LOCALE` (es_AR),
     `WHATSAPP_CLOUD_API_VERSION` (v21.0)

2. **`main.py`**
   - Import + `WhatsappCloudSender` (mismo patrón 502 que Vonage)
   - `_select_sms_sender`: branch `whatsapp_cloud`
   - **Default** `OTP_SMS_PROVIDER` sigue en `"dev"` (sin tráfico real)

## Intactos

- `sms_vonage.py`, `whatsapp_vonage.py`
- Flujo OTP / `OTP_MAX_VERIFY_ATTEMPTS`
- `requirements.txt` (ya tiene `requests==2.32.3`)

## Activar en Render (cuando haya credenciales Meta)

```
OTP_SMS_PROVIDER=whatsapp_cloud
WHATSAPP_CLOUD_TOKEN=...
WHATSAPP_CLOUD_PHONE_NUMBER_ID=...
WHATSAPP_CLOUD_TEMPLATE_NAME=<plantilla_aprobada>
WHATSAPP_CLOUD_TEMPLATE_LOCALE=es_AR
```

## git diff --stat (real)

```
 apps/api/app/main.py           |  14 ++++++++++++++
 apps/api/app/whatsapp_cloud.py | 114 ++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 128 insertions(+)
```
