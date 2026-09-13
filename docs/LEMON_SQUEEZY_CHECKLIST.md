# Lemon Squeezy — checklist operativo (Propomi)

La cuenta está **en verificación**. No hace falta código nuevo hasta que aprueben.
El backend ya tiene gateway + webhook (`POST /payments/webhooks/lemonsqueezy`).

## 1. Cuando aprueben la cuenta (Dashboard Lemon)

1. **Store** activo y en la moneda/país que uses (USD recomendado para `PAY_PER_LEAD_USD = 5`).
2. Crear un **Product** de un solo pago, por ejemplo: `Propomi — Revelar contacto`.
3. Crear un **Variant** de ese product (precio **USD 5** o el valor que definan).
4. Anotar:
   - `STORE_ID` (Settings → Stores)
   - `VARIANT_ID` del variant de “1 reveal”
   - API key (Settings → API)

## 2. Webhook

1. Settings → Webhooks → **Add endpoint**
2. URL de producción:
   ```
   https://<TU-API-PUBLICA>/payments/webhooks/lemonsqueezy
   ```
   (el host de Render/API, no el de Vercel del front)
3. Eventos a suscribir (mínimo):
   - `order_created`
4. Guardar el **Signing secret** → será `LEMON_SQUEEZY_WEBHOOK_SECRET`.

El handler actual:
- Verifica `X-Signature` (HMAC-SHA256 del body con el secret).
- Solo actúa si `event_name == order_created` y `status == paid`.
- Lee `meta.custom_data.transaction_id` (lo manda `create_checkout`).
- Marca la `RevealTransaction` como `COMPLETED` y el `Offer.contact_revealed`.

## 3. Variables de entorno (API / Render)

| Variable | Uso |
|----------|-----|
| `LEMON_SQUEEZY_API_KEY` | Bearer para crear checkouts |
| `LEMON_SQUEEZY_STORE_ID` | Store |
| `LEMON_SQUEEZY_VARIANT_ID` | Variant del pay-per-lead |
| `LEMON_SQUEEZY_WEBHOOK_SECRET` | Firma del webhook |

Sin las tres primeras, el API sigue en **MockPaymentGateway** (402 sin `checkout_url` real).

Tras setearlas: **redeploy** del servicio API para que `_select_payment_gateway()` elija Lemon.

## 4. Prueba de humo (después del deploy)

1. Agencia **VERIFIED**, sin `free_leads_remaining` ni cupo de plan (o agotarlos).
2. Comprador crea una oferta.
3. Agente → **Revelar contacto** → debe responder **402** con `checkout_url` + `transaction_id`.
4. Abrir `checkout_url`, pagar con tarjeta de test de Lemon (si el modo test está disponible).
5. Confirmar que el webhook deja la transacción en `COMPLETED`:
   - `GET /payments/{transaction_id}/status` → `COMPLETED`
   - Reintentar reveal → contacto del comprador, sin nuevo cobro.
6. Revisar logs: no debe haber `Firma inválida` ni `Faltan variables`.

## 5. Qué NO hacer todavía

- No cablear suscripciones mensuales en Lemon hasta el ticket de planes (T5.x): el webhook hoy **ignora** eventos que no sean `order_created` de pay-per-lead.
- No poner el webhook secret en el frontend ni en repos públicos.
- No bajar `ENV=production` sin las 4 variables: en prod sin credenciales el mock no da checkout real.

## 6. Rollback rápido

Quitar del entorno `LEMON_SQUEEZY_API_KEY` (o las tres) y redeploy → vuelve el mock. Los reveals gratis / cupo de plan no dependen de Lemon.

---

**Estado actual del repo:** integración de código lista (checkout + webhook + status). Falta solo cuenta aprobada + env + webhook apuntando a la API pública.
