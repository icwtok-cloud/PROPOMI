# PROGRESS_LOG

## 2026-09-17

1. Clonado `main` de https://github.com/icwtok-cloud/PROPOMI (depth 1) → HEAD `2b8580ac7e12f69e0466addc576dfa422f0dfd75`.
2. Confirmado 593 × U+FFFD en 387 líneas de `apps/api/app/main.py` (lectura de bytes / count Python).
3. Extracción de todas las líneas afectadas y contextos.
4. Reconstrucción manual por contexto (español rioplatense / argentino): vocales acentuadas, ñ, em-dashes, signos de interrogación/exclamación donde correspondía.
5. Aplicación de reemplazos exactos (lista ordenada de strings corruptos → correctos). Iteraciones hasta residual = 0.
6. Verificación final:
   - `chr(0xFFFD)` count = 0
   - `git diff --stat` = 387 insertions / 387 deletions, solo main.py
   - Mensajes de error HTTPException revisados (Ingresá, Sesión, Verificá, válido, teléfono, código, etc.)
7. Empaquetado en estructura `repo_paths/...` + README + listado completo + diff.

No se tocó ninguna otra lógica, import, espaciado ni línea no afectada.

## 2026-09-17 — OTP WhatsApp Cloud API (Meta)

- Nuevo provider `whatsapp_cloud` (Graph API) por rechazo de tarjeta en Vonage.
- `whatsapp_cloud.py` + `WhatsappCloudSender` + branch en `_select_sms_sender`.
- Default `OTP_SMS_PROVIDER=dev` (apagado hasta credenciales Meta + plantilla).
- Vonage modules no borrados. requests ya en requirements.
