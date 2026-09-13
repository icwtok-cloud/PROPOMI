## 2026-09-13 — Etapa 3 v1: evento `search_performed`

- **Objetivo (roadmap sección 10, fase Intelligence):** loguear cada
  búsqueda/filtro del comprador de forma agregada y anónima, como insumo
  futuro de matching, recomendaciones, demanda y pricing intelligence.
- **Archivo pusheado:** `apps/api/app/main.py` → versión **v4**.
- **`ALLOWED_EVENTS`:** se suma `"search_performed"` al set de eventos
  válidos (permite además loguearlo manual vía `POST /events` si en el
  futuro hiciera falta, aunque el uso principal es automático — ver abajo).
- **`GET /properties`:** ahora loguea un `Event(name="search_performed")`
  en cada llamada, con:
  - `context.filters`: solo los filtros efectivamente usados en esa query
    (zone, type, operation, rooms, max_price, parking, credit, agency_id) —
    nunca texto libre, nunca datos de contacto.
  - `context.result_count`: cantidad de resultados que devolvió esa búsqueda.
  - `user_id` / `agency_id`: se completan solo si viene un header
    `Authorization` con una sesión válida (opcional — la búsqueda funciona
    igual sin login, típico caso de comprador anónimo navegando).
  - Nuevo parámetro opcional `session_id` (mismo patrón que ya usa
    `POST /events`) para poder agrupar búsquedas de una sesión anónima sin
    necesitar cuenta.
  - Si el `Authorization` viene vencido/inválido, la búsqueda **no falla**
    — se ignora la sesión y se loguea igual sin `user_id` (una búsqueda
    nunca debe romperse por un token viejo).
- **No se tocó:** el filtrado de propiedades en sí (misma lógica de antes),
  `prop_dict()`, ni ningún otro endpoint. Cambio acotado a `GET /properties`
  y a la constante `ALLOWED_EVENTS`.
- **Validado en este entorno (Claude), no en la máquina del usuario:**
  `python3 -m py_compile` sobre el archivo completo → sin errores de
  sintaxis. **No se pudo importar el módulo real ni correr `pytest`** (sin
  acceso a red/pip en este entorno) — el usuario no tiene ambiente de test
  local tampoco (ver `CLAUDE.md`), así que la primera corrida real es en
  Render. Si el deploy falla o `pytest` local encuentra algo, pegar el
  error acá.
- **Pendiente / no se tocó en esta etapa:**
  - No hay todavía ningún endpoint que LEA/agregue `search_performed` para
    mostrar demanda (ej. "zonas más buscadas") — por ahora solo se graba el
    evento. Eso queda para una parte chica futura de la fase Intelligence
    (ej. sumarlo a `/analytics/summary` o un endpoint nuevo de demanda).
  - No se agregó nada en el frontend (`apps/web`) — el evento se genera
    solo del lado del backend en cada llamada real a `GET /properties`, sin
    necesitar que el frontend mande nada nuevo.
- **Próxima etapa a encarar (roadmap sección 10):** definir con el usuario
  si conviene primero exponer esta demanda agregada (ej. endpoint de "zonas
  más buscadas" para agencias) o seguir con otro punto de la fase
  Intelligence — a confirmar antes de arrancar la siguiente parte chica.
- Archivos tocados: `apps/api/app/main.py` (v4), `PROGRESS_LOG.md` (v8 —
  este mismo archivo).

---

# Progress Log — Propomi

Este archivo es el historial vivo del proyecto. Se agrega una entrada nueva
cada vez que se cierra y pushea una parte del trabajo. Entrada más reciente
arriba. No se borran entradas viejas.

Formato de cada entrada:

```
## [fecha] — [etapa del roadmap tocada]
- Qué se hizo
- Qué quedó pendiente / no se llegó a hacer
- Decisiones tomadas sobre la marcha (y si son reversibles)
- Archivos tocados
```

---

## 2026-09-13 — Infraestructura: proyecto de Render creado y configurado

- El usuario creó el Blueprint de Render para `propomi-api` a partir de
  `render.yaml` y además un **Environment Group** en Render con las 4
  variables necesarias: `DATABASE_URL` (apuntando a la instancia Postgres
  ya creada), `CORS_ORIGINS`, `ENV=production`, `JWT_SECRET` (valor random
  generado, no el default inseguro de desarrollo).
- **Nota de seguridad:** el valor concreto de `JWT_SECRET` circuló en el
  chat de esta sesión (el usuario compartió una captura con el valor
  visible). No es explotable por sí solo sin acceso a la base de datos,
  pero **se recomienda rotarlo en Render** (Environment Group → editar la
  variable → cualquier valor random nuevo) en cuanto termine de probar el
  flujo actual — rotar invalida todas las sesiones activas (JWT firmados),
  así que no hacerlo en medio de una prueba.
- **Pendiente de confirmar por el usuario:** que `/health` en la URL real
  de Render devuelva `"version":"1.3.0"` (confirma que el código de la
  Etapa 2 quedó desplegado, no una versión vieja).
- No hubo cambios de código en esta entrada — es un registro de
  infraestructura para que la próxima sesión sepa que Render ya existe y no
  hay que volver a explicar cómo crearlo.
- Archivos tocados: `PROGRESS_LOG.md` (este mismo, v7).

---

## 2026-09-13 — Etapa 2: Login de Google + verificación de celular del comprador

- **Objetivo (roadmap sección 10, punto 2 / decisión 6.2.1):** agregar
  Google Sign-In para el comprador, reutilizando el sistema de OTP existente
  para verificar el celular, ambos pedidos recién en el ÚLTIMO paso del
  wizard de oferta (antes de "Enviar oferta"), nunca al entrar al sitio.
- **Backend (`apps/api/app/main.py` → v3):**
  - Nuevas columnas en `User`: `phone_verified_at`, `email`, `google_sub`,
    `google_verified_at`. Migradas vía `ensure_schema_columns` (no rompe
    datos existentes — todo nullable/default NULL).
  - Refactor: se extrajo `consume_valid_otp()` de adentro de
    `/auth/otp/verify` para poder reusar la validación de código (rate
    limit, expiración, intentos) sin duplicar lógica.
  - Nuevo `POST /auth/otp/verify-buyer`: verifica el celular del comprador
    con el mismo código OTP, pero SIN exigir que el teléfono esté asociado
    a una agencia (a diferencia de `/auth/otp/verify`, que sigue siendo
    exclusivo de agentes y no se tocó en su comportamiento). Reemplaza la
    sesión guest anónima por una sesión atada al celular real.
  - Nuevo `POST /auth/google`: valida el ID token de Google Identity
    Services contra `GOOGLE_CLIENT_ID` (server-side, con la librería
    `google-auth`). Exige que la sesión ya tenga `phone_verified_at` seteado
    — no se puede vincular Google sin haber verificado el celular primero.
  - **Gate real en `POST /offers`:** ahora rechaza con 403 si el usuario no
    tiene `phone_verified_at` o `google_verified_at` — el chequeo del
    frontend es solo UX, esto es lo que de verdad lo impide.
  - **Bug encontrado y corregido en el momento (no llegó a pushearse roto):**
    si fallaba la conexión a los certificados públicos de Google
    (`googleapis.com`) al validar el token, la excepción
    `google.auth.exceptions.TransportError` no estaba capturada y tiraba un
    500 sin explicación. Ahora se distingue de un token inválido (401) y
    devuelve 503 con mensaje claro de reintentar.
  - `GOOGLE_CLIENT_ID` tiene como default el Client ID ya confirmado por el
    dueño del producto (no es secreto, viaja igual al navegador con GSI),
    pero se puede sobreescribir con la variable de entorno del mismo nombre
    en Render.
  - `requirements.txt` → v2: se sumó `google-auth==2.36.0`.
- **Frontend:**
  - `lib/google.ts` (nuevo, v1): helper para cargar el script de Google
    Identity Services una sola vez y renderizar el botón de Sign-In.
  - `lib/types.ts` → v2: `BuyerProfile` suma `phoneVerified`/`googleVerified`
    (espejo local de lo que ya valida el backend, solo para UX — no es la
    fuente de verdad).
  - `lib/api.ts` → v2: se exportó `setBuyerSession` (antes privada) y se
    sumaron `verifyOtpBuyer()` y `linkGoogleIdentity()`.
  - `components/OfferModal.tsx` → v2: el wizard pasa de 4 a 5 pasos. El
    paso 4 (resumen) ahora dice "Continuar" en vez de "Enviar oferta"; el
    paso 5 nuevo pide verificar celular por SMS y confirmar cuenta de
    Google, y recién ahí habilita "Enviar oferta".
  - `.env.example` → v2: se documentó `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
    (opcional, ya tiene default en código).
- **Validado en este entorno (Claude), no en la máquina del usuario:**
  - `python3 -m py_compile` + import real del módulo con `google-auth`
    instalado → sin errores.
  - Flujo end-to-end contra una DB sqlite descartable: pedido de OTP,
    verificación de comprador, bloqueo correcto de oferta sin Google (403),
    manejo correcto de OTP incorrecto (400), y confirmación de que el login
    de agente existente sigue funcionando exactamente igual (no se rompió
    nada).
  - `npx tsc --noEmit` sobre todo `apps/web` → 0 errores de tipos.
  - **Esto NO reemplaza correr `pytest` (8 tests existentes en
    `apps/api/tests/test_security.py`) ni `npm run build` real en el
    entorno de despliegue** — el usuario no tiene ambiente de test local
    (ver `CLAUDE.md` v4), así que la primera vez que esto corre "de verdad"
    es en Render/Vercel. Si algo falla ahí, pegar el log acá.
- **Pendiente / no se tocó en esta etapa:**
  - No hay forma de "desvincular" Google ni cambiar el email vinculado
    (no pedido, no bloqueante).
  - Caso borde no resuelto explícitamente: si un mismo teléfono ya es
    AGENTE y esa persona intenta ofertar como comprador, `verify-buyer`
    reutiliza la misma fila de `User` sin cambiarle el rol — funciona, pero
    no se probó ese camino específico end-to-end.
  - Panel de revisión manual de agencias sigue siendo Etapa 4, no se tocó.
- **Próxima etapa a encarar (roadmap sección 10):** Etapa 3 — evento
  `search_performed` (loguear búsquedas/filtros del comprador de forma
  agregada y anónima).
- Archivos tocados: `apps/api/app/main.py` (v3), `apps/api/requirements.txt`
  (v2), `apps/web/lib/google.ts` (nuevo, v1), `apps/web/lib/types.ts` (v2),
  `apps/web/lib/api.ts` (v2), `apps/web/components/OfferModal.tsx` (v2),
  `apps/web/.env.example` (v2).

---

## 2026-09-13 — CLAUDE.md v5: regla de trabajo en partes chicas

- El usuario reportó que sesiones largas de código se cortan antes de
  pushear nada, obligando a reempezar de cero. Se agregó una sección nueva
  y explícita: nunca encarar una etapa completa en un solo tramo largo,
  cortar en entregas chicas (idealmente pusheables una por una), y avisar
  antes de arrancar si una etapa no se puede partir así sin dejar el repo
  roto a medio camino.
- Archivos tocados: `CLAUDE.md` (v5).

---

## 2026-09-13 — CLAUDE.md v4: frase de arranque explícita + sin ambiente de test

- El usuario confirmó dos cosas nuevas que no estaban documentadas: (1) con
  solo decir "acá está el repo, seguí las instrucciones" en cualquier sesión
  nueva alcanza para arrancar a ejecutar directo, sin volver a preguntar
  nada ya fijado; (2) no tiene ambiente de test instalado localmente (ni
  `pytest` ni `npm run build` corren en su máquina).
- **Corrección aplicada en `CLAUDE.md` (ahora v4):** sección nueva al
  principio con la frase de arranque explícita, y sección ampliada sobre por
  qué no hay Claude Code conectado, ahora incluyendo la limitación de no
  poder correr tests localmente y sus consecuencias (checklist de calidad
  por revisión manual, primer despliegue real = primera corrida real).
- Archivos tocados: `CLAUDE.md` (v4).

---

## 2026-09-13 — Corrección de proceso: nombres de descarga únicos

- El usuario marcó que `CLAUDE.md` y `PROGRESS_LOG.md` se venían entregando
  siempre con el mismo nombre de descarga, lo cual en Windows genera
  `(1)`, `(2)` automáticos y obliga a borrar/renombrar a mano cada vez.
- **Corrección aplicada en `CLAUDE.md` (ahora v3):** todo archivo que se
  entrega para bajar —incluidos los "fijos" como `CLAUDE.md` y
  `PROGRESS_LOG.md`— lleva de acá en más un sufijo de versión único en el
  nombre de descarga (`CLAUDE_v3.md`, `PROGRESS_LOG_v3.md`, etc.). El paso
  de PowerShell que copia el archivo al repo es el que le pone el nombre
  final correcto sin sufijo.
- Archivos tocados: `CLAUDE.md` (v3), `PROGRESS_LOG.md` (v3 — este mismo
  archivo).

---

## 2026-09-13 — Etapa 1 v2: modelo de datos ampliado (apps/api/app/main.py)

- **Archivo pusheado:** `apps/api/app/main.py` → versión **v2** (la anterior,
  la que ya estaba en el repo, queda como v1 de referencia en este log).
- **Agregado sobre `Agency`:** `verification_status` (PENDING/VERIFIED/
  REJECTED, default PENDING), `instagram`, `website_link`,
  `verification_priority`, `verification_reviewed_at`,
  `verification_notes`, `free_leads_remaining`. El booleano `verified`
  viejo se deja como DEPRECATED (no se borra, para no romper nada que ya
  lo lea) pero deja de ser la fuente de verdad.
- **Agregado sobre `Property`:** `images` (lista JSON, hasta
  `MAX_PROPERTY_IMAGES = 5`) y `origin_published_at` (antigüedad declarada
  por el portal de origen, separada de `detected_at` que ya existía).
  `freshness` e `image` (singular) quedan DEPRECATED pero no se borran.
- **Migración de datos:** `migrate_legacy_property_images()` corre una vez
  al iniciar el proceso y completa `images=[image]` en toda fila vieja que
  todavía tenga `images` vacío — se eligió migrar el dato viejo, no
  arrancar de cero (doc 06 / 04.2).
- **Conectado `reveal_contact`:**
  - Ahora bloquea con 403 si `agency.verification_status != "VERIFIED"`
    (antes no existía ningún chequeo de verificación acá — un agente recién
    creado ya podía revelar contacto, lo cual contradecía la decisión 6.2.2
    del plan maestro).
  - Consume `free_leads_remaining` antes que el cupo de suscripción o el
    pay-per-lead, para los primeros 10 reveals gratis al verificarse (doc
    06.2.3 / 08). Es un contador separado, no se pisa con el cupo de plan.
- **`PATCH /agencies/{id}`** ahora acepta `instagram` y `website_link` para
  que la agencia pueda cargarlos desde "Mi cuenta" — la cola de revisión
  manual en sí (aprobar/rechazar) queda para la Etapa 4, no se construyó
  todavía.
- **Bug encontrado y corregido (no estaba documentado en la sección 12 del
  plan maestro):** la función `offer_action` (aceptar / rechazar /
  negociar una oferta) no tenía decorador `@app.post(...)` — el endpoint
  nunca estuvo expuesto en la API, solo funcionaban `/counter` y
  `/reveal`. Se agregó `@app.post("/offers/{offer_id}/{action}")`.
- **Pendiente / no se tocó en esta etapa:**
  - Panel interno de revisión manual (Etapa 4).
  - `Subscription` como tabla separada (se mantiene el enfoque actual de
    campos inline en `Agency` — funciona igual, se puede migrar a tabla
    propia más adelante si hace falta reportar historial de ciclos).
  - No se pudo correr `pytest` ni levantar el servidor en este entorno
    (sin acceso a red/pip) — **el usuario tiene que correr el checklist de
    la sección 11 del plan maestro localmente** (`pytest` +
    `npm run build` si tocó frontend) antes de pushear, y avisar acá si
    algo falla.
- Archivos tocados: `apps/api/app/main.py` (reemplazo completo → v2),
  `CLAUDE.md` (v2 — se agregaron las reglas fijas de entrega: PowerShell
  exacto, zip si son varios archivos, versionado creciente por archivo).

---

## 2026-09-13 — Etapa 0: setup del sistema de trabajo colaborativo

- Se leyó completo el documento maestro (`Propomi-Documento-Maestro.docx`)
  provisto por el dueño del producto y se copió sin cambios de contenido a
  `docs/PLAN_MAESTRO.md` dentro del repo, para que quede versionado junto
  al código en vez de vivir solo como un Word suelto.
- Se creó `CLAUDE.md` con las instrucciones de cómo debe operar cualquier
  sesión de IA que retome este repo.
- Se creó este archivo (`PROGRESS_LOG.md`) como historial vivo.
- **Decisión operativa (reversible):** por ahora no hay Claude Code
  conectado a este repo. El trabajo se hace en un chat normal de Claude.ai:
  el usuario pega el archivo puntual a tocar, Claude devuelve el reemplazo
  completo, el usuario aplica/testea/commitea/pushea localmente. Si en el
  futuro se conecta Claude Code, este flujo se reemplaza por trabajo directo
  sobre el repo clonado.
- **Próxima etapa a encarar (según roadmap, sección 10 del plan maestro):**
  Etapa 1 — Modelo de datos ampliado (`AgencyPhone`, verificación en dos
  niveles + Instagram/link, `Property.images` como lista, `Subscription` y
  `LeadCredit`, separar `freshness` en `detected_at`/`origin_published_at`).
  Todavía no se tocó ningún archivo de código.
- Archivos tocados: `CLAUDE.md` (nuevo), `PROGRESS_LOG.md` (nuevo),
  `docs/PLAN_MAESTRO.md` (nuevo).
