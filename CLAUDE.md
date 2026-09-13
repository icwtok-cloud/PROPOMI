# Instrucciones para Claude (o cualquier IA) trabajando en este repo

Si estás leyendo esto porque el dueño del producto compartió este repo y dijo
algo como **"Seguí las instrucciones y continuemos"**, hacé esto en orden:

1. Leé completo `docs/PLAN_MAESTRO.md` — es el brief de negocio + producto +
   arquitectura completo. Asume que no sabés nada del proyecto. No te saltees
   secciones, en particular la sección 5 (reglas no negociables de privacidad)
   y la sección 11 (checklist de calidad).
2. Leé completo `PROGRESS_LOG.md` — ahí está el historial real de qué se
   entregó, en qué etapa del roadmap vamos, y qué decisiones se tomaron sobre
   la marcha. El roadmap oficial (orden de dependencia) está en la sección 10
   de `docs/PLAN_MAESTRO.md`; `PROGRESS_LOG.md` te dice en qué punto de ese
   roadmap está el repo HOY.
3. Confirmá con el usuario en qué etapa retomar (por default: la primera
   etapa del roadmap que no esté marcada como cerrada en `PROGRESS_LOG.md`).
4. Trabajá en partes chicas, un archivo o un grupo chico de archivos por vez
   — nunca prometas ni asumas cambios sobre archivos que no viste.

## Por qué existe este archivo

No hay una herramienta de código (Claude Code) conectada a este repo todavía
— el trabajo se hace pegando archivos en un chat normal de Claude.ai. El flujo
real es:

1. El usuario pega o sube el archivo puntual del repo que hay que tocar para
   la etapa en curso (ej. `apps/api/app/main.py` para agregar un modelo
   nuevo).
2. Claude devuelve el archivo completo listo para reemplazar (o instrucciones
   de edición muy precisas), respetando el checklist de la sección 11 del
   plan maestro.
3. El usuario aplica el cambio localmente, corre `pytest` / `npm run build`,
   y si todo pasa, hace `git commit` + `git push` él mismo.
4. Después de cada push, Claude agrega una entrada nueva en
   `PROGRESS_LOG.md` (fecha, qué se hizo, qué falta, qué decisiones quedaron
   tomadas) — esto es lo que le permite a una sesión futura, con cero
   contexto previo, retomar exactamente donde quedó.

## Reglas que nunca se rompen (resumen — el detalle está en la sección 5 del plan maestro)

- El comprador nunca escribe texto libre para condiciones de compra.
- El agente nunca responde con texto libre (solo acciones estructuradas).
- Todo campo de comentario nuevo pasa por `sanitize_free_text()`.
- `buyer_name` / `buyer_phone` / `buyer_email` nunca viajan en una respuesta
  de API salvo `contact_revealed = true`.
- Identidad canónica de agente = teléfono E.164, no email.
- Canal B2B agente↔agente es siempre gratis y no puede usarse para reenviar
  un contacto de comprador ya capturado por el canal B2C pago.

## Cómo entregar cada etapa (reglas fijas, no volver a preguntar)

Rutas fijas de este usuario, ya confirmadas — usar siempre estas, sin
preguntar de nuevo:
- Repo local: `$env:USERPROFILE\Documents\PROPOMI`
- Todo archivo que Claude entregue para descargar cae en:
  `$env:USERPROFILE\Downloads`

Reglas de entrega, todas obligatorias:

1. **Windows + PowerShell siempre.** El usuario copia y pega, no adapta
   nada. Nunca dar comandos de bash/mac ni pedirle que "reemplace la ruta"
   — usar `$env:USERPROFILE\...` para que se resuelva solo.
2. **Versionado creciente por archivo.** Cada archivo que se reemplaza
   lleva un sufijo de versión que sube respecto de la entrega anterior de
   ESE archivo puntual (no un número global del proyecto): `main_v2.py`,
   `main_v3.py`, `OfferModal_v2.tsx`, etc. `PROGRESS_LOG.md` es la fuente
   de verdad de qué versión de cada archivo está pusheada.
3. **Si la entrega incluye más de un archivo, empaquetar en un .zip** y
   los pasos de PowerShell tienen que incluir la extracción
   (`Expand-Archive`) antes de copiar cada archivo a su carpeta real dentro
   del repo — nunca asumir que el usuario sabe descomprimir y ubicar cada
   uno a mano.
4. **Los pasos de push van siempre completos y listos para pegar:** entrar
   a la carpeta del repo, copiar/mover cada archivo a su ruta real dentro
   de `apps/...`, `git add` de esos paths puntuales, `git commit` con un
   mensaje que incluya la etapa y la versión (ej. `"Etapa 1 v2: modelo de
   datos ampliado"`), `git push origin main`.
5. **Después de cada push confirmado, sumar una entrada nueva en
   `PROGRESS_LOG.md`** (nunca reemplazar entradas viejas) con lo que se
   hizo, qué versión de qué archivo quedó pusheada, y qué sigue.

## Si algo es ambiguo

No asumas en silencio, en especial en todo lo que toca privacidad de
contacto (sección 5) o dinero (secciones 6 y 8). Para el resto, la sección
6.2 del plan maestro ya trae defaults recomendados explícitos — usalos y
avisá que son reversibles, no te bloquees esperando confirmación.
