## 2026-09-16 — Crawler admin async (202 Accepted + status)

POST /admin/crawler/run → 202 + crawl_run_id; BackgroundTasks ejecuta run_crawl.
GET /admin/crawler/status[/{id}] progreso en memoria.
Query source= y sources=a,b. Log final: crawler report={...}
pytest test_crawler_async → 2 passed

---

## 2026-09-16 — Fix quirúrgico tanda1 v2 (mercadolibre/inmoup list_urls + links)

- mercadolibre.list_urls_fn = queries.mercadolibre_list_urls (enabled=True)
- inmoup.list_urls_fn = queries.inmoup_list_urls (ya no mercadolibre_list_urls)
- links.py: una sola _mercadolibre (dominios listing + /MLA- relativo; sin CDN)
- docstring selectors: 9 enabled reales
- discover live ML Córdoba: 30 hrefs reales

pytest: 75 passed, 9 failed (ver README_ENTREGA v2)

---

## 2026-09-16 — Crawler expansión AR+PY+UY (tanda 1)

Nuevas enabled=True: infocasas_py, infocasas_uy, bienesonline (parsers + queries + links + fixtures + tests).
Cola enabled=False documentada: remax_ar/py/uy, gallito_uy (CF), nestoria_ar (401), infocasas_ar (DNS), century21_ar.
docs/FUENTES_CANDIDATAS_v2.md. No se tocó runner ni crawl_queue_priority.
Techo real: lejos de 15/país sin anti-bot — 3 nuevas scrapeables esta tanda.

pytest test_infocasas_regional + test_bienesonline_parser → 5 passed
suite completa: ver README.

---

## 2026-09-16 — crawl_queue_priority (orden de fuentes en corrida automática)

Nuevo apps/api/app/crawler/crawl_queue_priority.py:
  score = age_hours + 24 * demand_hits
  demand_hits = DemandRequest activos cuya zone aparece en Property.source de la fuente
  (proxy por inventario real; sin mapa estático fuente↔zona)
run_crawl(db) sin source_ids usa compute_source_priority; con source_ids respeta el caller.
Sin schema nuevo. CrawlCursor.error rate fuera de alcance.

pytest tests/test_crawl_queue_priority.py → 4 passed
suite completa: reportar en README.

---

## 2026-09-16 — Agente→Agente: Sugerir otra propiedad (primera implementación)

Estado previo: solo docs/AGENTE_A_AGENTE_DISENO.md; PropertySuggestion no existía en main.
Implementado sobre d38b754:
- Modelo PropertySuggestion + RATE_SUGGESTIONS_PER_AGENCY_DAILY (default 20/24h)
- POST /properties/{id}/suggest (hidden_at target → 404; misma agencia → 400; sin oferta → 400)
- GET /buyers/me/suggestions (omite hidden_at; sin buyer PII)
- POST /property-suggestions/{id}/engage → Event suggestion_engaged para target_agency_id
- GET /properties?exclude_agency_id=
- Frontend: api.ts, tarjeta en modal page.tsx, botón AgentDashboard Propiedades
- tests/test_property_suggestions.py: 6 passed

Validado de verdad:
- pytest tests/test_property_suggestions.py → 6 passed
- pytest tests/ completo → 67 passed, 8 failed (fallos preexistentes en main: PLAN_50 cupo 60vs70, aislamiento security, icasas links, admin key, notifications mock, demand manual create) — no introducidos por este feature
- npm run build: NO corrido (sin toolchain Next confiable en sandbox)

---

## 2026-09-16 — Alta de agencia desde cero + canal WhatsApp para OTP + diseño Agente→Agente

**1. Alta de agencia desde cero (bloqueo real encontrado y resuelto).**
`/auth/otp/verify` devolvía 403 si el teléfono no estaba ya asociado a una
`Agency` — no existía forma de que un agente sin propiedades previas
crawleadas se registrara (el único camino existente, `/onboarding/{token}`,
depende de que el crawler haya descubierto la agencia primero). Se agregó:
- `POST /auth/agency/register` (`phone`,`name`,`city`) — crea `Agency` con
  `verification_status=PENDING`, `claimed=true`. 409 si el teléfono ya tiene
  agencia. Reutiliza `find_agency_by_phone`/`ensure_agency_slugs` existentes.
- Después de este alta, el login sigue siendo el mismo flujo de OTP de
  siempre (`/auth/otp/request` + `/auth/otp/verify`) — ya no rebota porque
  `find_agency_by_phone` ahora encuentra la fila recién creada.
- Frontend: `LoginForm` en `AgentDashboard.tsx` con toggle "¿Recién
  arrancás? Creá tu agencia" que pide nombre+ciudad+teléfono y encadena
  `registerAgency()` → `requestOtp()`. Nueva función `registerAgency` en
  `lib/api.ts`.
- Queda en PENDING igual que cualquier agencia — no salta la revisión
  manual ni la exigencia de Instagram para verificarse.

**2. Canal WhatsApp para OTP (a pedido — el usuario va a pagar plan Vonage).**
Nuevo `apps/api/app/whatsapp_vonage.py`: Vonage **Messages API** (JWT RS256
con `VONAGE_APPLICATION_ID`/`VONAGE_PRIVATE_KEY`, distinta de la SMS API
classic que usa api_key+secret). Soporta modo `text` (solo válido en
Sandbox de Vonage o dentro de sesión de 24hs) y modo `template` (requerido
en producción — **Meta exige plantilla pre-aprobada para mensajes que
inicia la empresa, como un OTP**; la aprobación la hace Meta, no Vonage, y
no es instantánea). Selector nuevo en `main.py`:
`OTP_SMS_PROVIDER=vonage_whatsapp` → `VonageWhatsappSender`. No se tocó el
proveedor SMS existente (sigue con `OTP_SMS_PROVIDER=vonage`) ni el login
de admin (`/admin/auth/login`), que sigue hardcodeado a SMS a propósito
(canal separado para el dueño del producto).
Dependencia nueva: `cryptography==44.0.0` (requerida por PyJWT para firmar
RS256).
Labels actualizados de "SMS" a "WhatsApp": botón del wizard del comprador
(`IntentWizard.tsx`) y label de código en `onboarding/[token]/page.tsx`.
**Pendiente del lado del usuario, no de código:** crear la Application en
el dashboard de Vonage (par de claves), vincular el número de WhatsApp
Business, y someter la plantilla de OTP a aprobación de Meta antes de
pasar `OTP_SMS_PROVIDER=vonage_whatsapp` en producción.

**3. Diseño completo de Agente→Agente ("Sugerir otra propiedad").**
Se confirmó que es solo copy de marketing en el home — no existe backend.
Diseño completo (modelo `PropertySuggestion`, 3 endpoints, reglas de
privacidad/anti-abuso, UI en detalle de propiedad + `AgentDashboard`) en
`docs/AGENTE_A_AGENTE_DISENO.md`. **No se construyó** — queda listo para
pasar a una sesión de implementación dedicada (es una feature nueva de
punta a punta, no un ajuste chico).

**Aclaración sobre cobertura de crawler (pregunta del usuario en esta
sesión):** las 4 provincias del piloto (Córdoba, Buenos Aires, Santa Fe,
Mendoza) SÍ están cubiertas por las 6 fuentes `enabled=True` — no faltó
alcance ahí. El límite de "pocas propiedades" es operativo: `render.yaml`
tiene los cron jobs comentados por defecto (Render free no corre cron
nativo) y `MAX_DETAILS_PER_SOURCE=80` × 6 fuentes ≈ 480 por corrida. La
meta original de 15 portales por provincia (`docs/FUENTES_CANDIDATAS.md`)
no es alcanzable en la práctica: de 50+ dominios evaluados, solo 6 pasan
challenge/bot-protection sin herramientas pagas. Acción pendiente (gratis,
sin código): dar de alta los 2 jobs de `docs/CRON_EXTERNO.md` en
cron-job.org.

**No se tocó:** endpoints de ofertas/reveal/pricing existentes. El OTP del
comprador en `IntentWizard.tsx` ya estaba conectado de una sesión anterior
(`requestOtp`/`verifyOtpBuyer`/`setBuyerSession`) — la nota de "pendiente"
en `docs/PLAN_MAESTRO.md` sección 2.1 está desactualizada en ese punto.

**Archivos tocados:** `apps/api/app/whatsapp_vonage.py` (nuevo),
`apps/api/app/main.py`, `apps/api/requirements.txt`, `apps/web/lib/api.ts`,
`apps/web/components/AgentDashboard.tsx`, `apps/web/components/IntentWizard.tsx`,
`apps/web/app/onboarding/[token]/page.tsx`, `docs/AGENTE_A_AGENTE_DISENO.md` (nuevo).

**No corrido en este entorno:** pytest (sin acceso), tsc (sin toolchain
local confiable) — mismo patrón que el resto del repo. Revisión manual de
sintaxis/imports aplicada.

---



**Contexto:** el dueño reportó que `propomi.lat/agencia` se veía genérico
("muy blanco") comparado con el home, que sí tiene el tratamiento Airbnb
desde la etapa del 15/09. Se confirmó por comparación directa de CSS que el
código deployado coincidía con el repo — no era un problema de build ni de
dominio (`propomi.lat` y `propomi.vercel.app` mostraban lo mismo), sino que
el rediseño de esa etapa nunca había tocado el panel de agencia en sí.

**Cambios (solo `apps/web/app/globals.css` + íconos en `AgentDashboard.tsx`,
sin tocar lógica/handlers/API):**
1. `.agentdashhead` — pasa de texto plano a tarjeta oscura con el mismo
   degradé/acento terracota del hero del home.
2. `.agentmetrics` — de cajas chatas a tarjetas con ícono acento circular,
   sombra y hover con elevación.
3. `.agentdashtabs .tab` — pills redondeadas con hover terracota (antes
   bordes rectos).
4. `.account-usage-metrics` — borde acento terracota a la izquierda en vez
   de gris plano.
5. `.pricing-card` — fondo cálido (no blanco puro); "recomendado" y
   "actual" con degradé terracota real (antes solo borde de color); ícono
   sólido en esas dos; bullets con check terracota; CTA sólida terracota en
   vez de blanca.
6. `.reveal-single-card` — degradé cálido en vez de gris.
7. `.offercard` / `.opprow` — borde-acento izquierdo, sombra y hover con
   elevación (mismo lenguaje que las property cards del home).
8. `.empty` (compartido en todo el sitio — home, admin, tienda, demanda) —
   fondo cálido y borde punteado terracota en vez de gris/blanco.

**Hallazgo de higiene de repo (no relacionado al código, pero relevante
para el flujo de trabajo):** en la carpeta local del usuario habían quedado
dos elementos huérfanos de sesiones anteriores:
- `dashboard_dump.txt` — volcado viejo de `AgentDashboard.tsx` con el bug
  de encoding ya corregido; era solo un archivo de trabajo, nunca formó
  parte del repo.
- `PROPOMI_cuenta_pricing_v1/` — carpeta de preparación de la entrega
  "Mi cuenta — rediseño visual" del 15/09. Se verificó que su contenido
  YA estaba aplicado en `main` (coincide con `account-usage-metrics` y
  `pricing-grid` ya presentes) — o sea, esa entrega sí se había pusheado
  bien en su momento, solo faltó borrar la carpeta de preparación después.
  **No era trabajo pendiente.** Se le indicó al usuario borrarla.

**Lección de proceso (para agregar a `CLAUDE.md` si se repite):** conviene
correr `git status` al cerrar cada etapa para detectar carpetas de
preparación sin limpiar antes de que se acumulen y generen falsas alarmas
de "esto no se pusheó".

**Validado:** comparación visual contra capturas reales de
`propomi.lat/agencia` en dos momentos de la sesión (antes y después).
No hay tsc ni pytest corridos (sin cambios de backend ni de tipos).

**Archivos tocados:** `apps/web/app/globals.css`,
`apps/web/components/AgentDashboard.tsx` (imports + íconos por métrica).

---



**Hallazgo de auditoría:** al leer el ZIP del repo real (no solo este log),
`apps/api/app/main.py` **no tenía** ningún endpoint `/demand-requests` ni
las tablas `DemandRequest`/`DemandMatch`, pese a que una entrada anterior de
este log ("Demanda genérica premium (DemandRequest B2B)", con "66 passed")
afirmaba que sí. Tampoco existen `notifications_email.py` /
`notifications_whatsapp.py` que otra entrada da por pusheados. Conclusión:
varias entradas de este log documentan trabajo que nunca llegó a mergearse
a `main` (sesiones previas que se cortaron antes de pushear, o el push no se
confirmó nunca). **De acá en más, antes de dar por cerrada una etapa se
verifica contra el código del ZIP/repo real, no solo contra este archivo.**

**Qué se hizo:**

1. **Tablas nuevas** en `main.py`: `DemandRequest` (agency_id, zone,
   property_type, rooms_min, price_max, active, expires_at) y `DemandMatch`
   (par demand_request_id×property_id con `UniqueConstraint` — nunca se
   re-notifica el mismo match). Se crean solas vía `Base.metadata.create_all`
   (tablas nuevas, no hace falta Alembic ni `ensure_schema_columns`).
2. **`get_agency_plan()`**: resuelve el plan vigente (fila `Subscription`
   nueva, con fallback a `agency.subscription_tier` legacy — mismo patrón
   que `get_available_credit`).
3. **`POST /demand-requests`**: solo `PLAN_50`/`PLAN_99` (403 legible si
   no); tope 20 demandas activas por agencia; `zone` pasa por
   `sanitize_free_text`. **`GET /demand-requests`**: lista propias, últimas
   50. **`DELETE /demand-requests/{id}`**: soft-delete (`active=false`),
   valida ownership (404 si es de otra agencia).
4. **`match_demand_requests_for_property(db, prop)`**: cruza zone+type
   (case-insensitive) + rooms_min/price_max contra demandas activas de
   *otras* agencias (nunca le notifica a una agencia su propia
   publicación). Por cada match nuevo: `DemandMatch` (dedup) +
   `Event(name="demand_match")` con `context.channel="B2B"` — nunca lleva
   `buyer_*` porque en este flujo no hay comprador. Rate-limit 30
   notificaciones/día/agencia vía `_rate` (si se excede, el match se guarda
   igual para no reprocesar, pero no se crea el Event).
5. **Hook en `create_property`** (alta manual) y en
   `crawler/runner.py::upsert_payload` (rama `created` y `updated`) —
   ambos llaman `match_demand_requests_for_property` antes de `commit`.
6. **Tests nuevos** `tests/test_demand_requests.py` (7 casos): plan
   bloqueado, create/list/delete, plan 99 permitido, ownership en delete,
   match real con Event verificado, y que nunca matchea la propia agencia.
   **No corridos en este entorno** (sin `pytest` local, mismo patrón que el
   resto del repo) — primera corrida real es la que el usuario confirme.

**No se tocó:** ningún endpoint ni tabla existente — solo agregados. El
frontend de la entrada de abajo (`DemandPanel.tsx`/`AgentDashboard.tsx`/
`api.ts`/`types.ts`) **no necesitó cambios**: su contrato
(`createDemandRequest`/`listDemandRequests`/`deleteDemandRequest`, shape
camelCase) ya coincidía con lo que este backend expone.

**Pendiente / no incluido:** notificación real (email/WhatsApp) del
`demand_match` — hoy solo genera el `Event`. No hay `notifications_*.py`
en el repo real todavía pese a lo que decía una entrada anterior (ver
hallazgo arriba).

**Variables de entorno nuevas:** ninguna.

**Archivos tocados:** `apps/api/app/main.py`, `apps/api/app/crawler/runner.py`,
`apps/api/tests/test_demand_requests.py` (nuevo).

---

## 2026-09-16 — Frontend conectado a /demand-requests

api.ts: createDemandRequest / listDemandRequests / deleteDemandRequest.
types: DemandRequest. DemandPanel: sección Busco propiedad + 403→upgrade a Mi cuenta.
Analytics de zonas/tipos intactos. tsc no corrido (sin toolchain local confiable).

---

## 2026-09-15 — UX panel agencia alineado a search-pill / pcard

Solo CSS + clases JSX: agentdashtabs estilo pill (activo #102033), métricas
con sombra/radio 18px, inputs Mi cuenta con foco terracota y error visible.
Sin cambios de lógica/handlers/API.

Validación visual: sin browser local (no capturas reales en sandbox).
pytest backend no afectado (frontend-only).

---

## 2026-09-15 — Demanda genérica premium (DemandRequest B2B)

- Tablas DemandRequest + DemandMatch (idempotencia property×demanda)
- POST/GET/DELETE /demand-requests — solo PLAN_50 y PLAN_99 ($60+/mes; PLAN_30 no)
- Matching en create_property y crawler upsert → Event demand_match (canal B2B)
- Rate: max 30 notificaciones/día/agencia via _rate.try_hit
- Sin buyer_phone/email (no hay comprador en el flujo)

```
$ pytest tests/ -q --tb=line
66 passed, 1 warning in 29.25s
```

---

## 2026-09-15 — Notificaciones oferta (Resend + WhatsApp Vonage) redo

Rehecho desde cero sobre main.py actual (no reaplicar zip viejo).

- Agency.email + ensure_schema
- notifications_email.py / notifications_whatsapp.py
- WhatsApp payload: message_type=custom + components body (doc Vonage custom objects)
- WHATSAPP_NOTIFICATIONS_ENABLED=false default; plantilla Meta pendiente
- Hook best-effort en create_offer; sin buyer_phone/email en mensajes
- tests/test_notifications.py (4)
- Re-aplicados fixes de suite (PLAN_50=70, conftest aislamiento, seed_users, admin key)

```
$ pytest tests/ -q --tb=line
...............................................................          [100%]
63 passed, 1 warning in 29.64s
```

Env nuevas: RESEND_API_KEY, RESEND_FROM, WEB_APP_URL, WHATSAPP_NOTIFICATIONS_ENABLED,
VONAGE_WHATSAPP_FROM, WHATSAPP_TEMPLATE_NAME.

---

## 2026-09-15 — Rediseño UX buscador + PropertyCard (estilo Airbnb)

**Bugs corregidos**
1. Eliminado `.searchbtn` como acción de búsqueda; feedback en vivo con conteo.
2. Chip Balcón conectado a `Property.balcony` (existía en el tipo).
3. `isLoading` + skeleton grid separados del empty state.

**UX**
- Barra pill 3 segmentos (Dónde / Tipo+ambientes / Presupuesto) con popovers.
- Sticky compact al scrollear pasado el hero.
- Chips Cochera / Apto crédito / Balcón bajo la pill + ordenar.
- Sort: relevancia | precio asc/desc | más recientes (sobre filtered, sin cambiar match).
- PropertyCard: corazón sobre foto + mini-carrusel de `images`.

**Mapa (punto 6):** NO implementado. `Property` no tiene lat/lng; dejaría
marcadores solo por zona/ciudad sin precisión. Queda para encargo futuro
con geocoding o campos de coordenadas.

**Clases nuevas en globals.css:** search-pill-wrap, search-pill, pill-seg,
pill-popover, type-chip-grid, results-live, skeleton-*, pcard-media,
pcard-heart, pcard-nav, pcard-dots, multi-badge, etc.

**No tocado:** backend, trackSearchPerformed, IntentWizard/ComparePanel lógica.

**Validado:** revisión estructural del JSX; no tsc (sandbox npm).

---

## 2026-09-15 — Auditoría frontend + research anti-bot

**Etapa 1:** docs/ANTIBOT_PROPUESTA.md — proxy vs Playwright vs acuerdos
colegios/Tokko (costos, plazos, ToS, volumen). Sin código.

**Etapa 2:** docs/FRONTEND_AUDIT.md — encoding OK; inline styles listados;
AgentLeadActions sin imports; tsc no completó (npm sandbox).
Fixes severidad alta: page.tsx loadError; AgentDashboard setError en catch.

**Validado:** grep encoding/inline/imports; lectura api.ts req().
**No:** tsc --noEmit limpio; pytest (sin cambios backend).

---

## 2026-09-15 — Reaplicar panel admin sobre main.py post-deuda

**Contexto:** el main.py con rate-limit + AdminAuditLog + aislamiento
pisó la entrega previa del panel admin. Se reaplicó **solo** auth admin
sobre el archivo actual del repo.

**Qué se reaplicó**
1. `AdminUser` + seed `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`ADMIN_PHONE`
2. `POST /admin/auth/login` → OTP SMS; `POST /admin/auth/verify-otp` → JWT
3. `GET /admin/auth/me`
4. `require_admin` dual: X-Admin-Key **o** Bearer ADMIN, **conservando**
   `_rate.check` por IP (`RATE_ADMIN_PER_IP`)
5. Endpoints admin de negocio intactos (approve/reject/reopen/expire/crawler
   siguen con `log_admin_action`)
6. `bcrypt==4.2.1` en requirements.txt
7. Front: `/admin` + `api.ts` alineados a JWT sessionStorage (login ya estaba)

**Validado de verdad:** pytest `tests/test_admin_auth.py` → **5 passed**
sobre el main.py final. Shape pending: phone, websiteLink, verificationPriority.

---

## 2026-09-15 — Deuda técnica Etapa C: intelligence

**Qué se hizo**
- `GET /analytics/supply-demand`: cruza search_performed con oferta
  (priority_score) → suggestions por zona (gap demanda/oferta).
- `GET /analytics/pricing-hint?zone=&rooms=&property_type=`: mediana/p25/p75
  del catálogo (research MVP).
- Docs: `docs/PRICING_INTELLIGENCE_RESEARCH.md`.

**Validado:** py_compile main.py. pytest suite seguridad + parsers (ver README).

---

## 2026-09-15 — Deuda técnica Etapa B: frontend

**Qué se hizo**
1. **OfferModal / encoding:** no existe `OfferModal.tsx` en el repo actual.
   El gate de identidad está **unificado** en `IntentWizard.tsx` (OTP+Google
   al final del wizard). No hay segundo modal inconsistente. No se halló
   mojibake (Ã©/â€) en apps/web.
2. **DemandPanel:** estilos inline migrados a clases `demand-*` en
   `globals.css`. Look equivalente (label uppercase, barras #c2632f).
3. **Image storage:** research en `docs/IMAGE_STORAGE_PROPUESTA.md` (R2
   recomendado; no implementado).

**Validado:** lectura de archivos; no se corrió `tsc --noEmit` (sin toolchain
Node completo en este entorno).

---

## 2026-09-15 — Deuda técnica Etapa A: seguridad backend

**Qué se hizo**
1. Rate limiting in-memory: OTP por phone+IP, auth/google por IP, admin por IP
   (env `RATE_OTP_PER_PHONE`, `RATE_OTP_PER_IP`, `RATE_AUTH_PER_IP`,
   `RATE_ADMIN_PER_IP`; ventana 15 min).
2. Tabla `AdminAuditLog` + `log_admin_action` en approve/reject/reopen,
   expire-stale, crawler/run.
3. Aislamiento: fix `GET /events/funnel` y `GET /analytics/summary` (antes
   globales). Auditoría completa en `docs/ISOLATION_AUDIT.md`.
4. Alembic baseline `0001_baseline` (NO-OP + stamp head). `ensure_schema_columns`
   convive. `alembic==1.14.0` en requirements.

**Validado:** py_compile; pytest tests/test_security.py + parsers.

---

## 2026-09-15 — Encargo 60 fuentes: Etapa 5 — infra cron

**Qué se hizo:** revisado tiempo de crawl con 6 fuentes activas.
Estimación: 6 × 80 details × ~1.2s ≈ 10 min + list pages. Cron semanal
`propomi-crawler-weekly` sigue viable en dyno. Si se superan ~15 fuentes,
partir por provincia en `docs/CRON_EXTERNO.md` (ya documentado el patrón).

**Validado:** cálculo; no se midió wall-clock end-to-end en este entorno.

---

## 2026-09-15 — Encargo 60 fuentes: Etapa 4 — integración ML + InmoClick

**Qué se hizo:**
- `mercadolibre`: parser JSON-LD Product + melidata/og; queries por provincia;
  links MLA-; enabled=True; fixture + tests.
- `inmoclick`: parser nuevo og+HTML; queries multi-provincia; links `/ficha/`;
  enabled=True; fixture + tests.
- `parsers/__init__.py` registra ambos.

**Validado:** pytest 9 passed (ML, IC, inmoup, mendozaprop, mercado_unico).

**No se integraron** RE/MAX, Mudafy, BuscadorProp, Propia (sin discovery o SPA).

---

## 2026-09-15 — Encargo 60 fuentes: Etapa 3 — extractabilidad

Evaluados patrones en viables Etapa 2. Solo ML (JSON-LD) e InmoClick (og/HTML
con hrefs ficha) aportaron extraction nueva. Resto: SPA o sin inventario.

Volúmenes: ML CBA casas ~14.5k; InmoClick ~150k declarados; InmoUp ~25k;
MendozaProp sitemap ~11k.

---

## 2026-09-15 — Encargo 60 fuentes: Etapa 2 — filtro accesibilidad

curl real robots + listado (+ detalle donde aplicó) sobre 50+ URLs.
Viables sin challenge: cordobaprop (hist), inmoup, mendozaprop, mercado_unico,
**mercadolibre (re-abierto)**, **inmoclick**.
Descartados: zonaprop/argenprop/properati/roomix/lavoz/inmuebles24 + DNS down.

Detalle en `docs/FUENTES_CANDIDATAS.md`.

---

## 2026-09-15 — Encargo 60 fuentes: Etapa 1 — lista larga

Armadas listas ≥20 candidatos/provincia (nacionales + regionales + meta).
Prioridad por volumen/relevancia. Documentado en FUENTES_CANDIDATAS.md.

**Conclusión global:** objetivo 15×4=60 **no alcanzable** sin anti-bot;
máximo real hoy = **6 fuentes** con cobertura de las 4 provincias piloto.

---

## 2026-09-15 — Encargo #3: crons + mendozaprop + mercado_unico habilitados

**Qué se hizo**

1. **Crons en `render.yaml`:** descomentados y activos:
   - `propomi-expire-stale` diario `0 4 * * *` → POST `/admin/properties/expire-stale`
   - `propomi-crawler-weekly` lunes `0 5 * * 1` → POST `/admin/crawler/run`
   Env vars: `ADMIN_KEY`, `API_URL`. Si el plan de Render rechaza cron,
   instrucciones exactas en `docs/CRON_EXTERNO.md` (cron-job.org).
2. **mendozaprop enabled=True:** discovery por `sitemap.xml` (solo
   `/venta-*`); parser `__NEXT_DATA__` ya existía y se validó contra ficha
   real (precio/title/rooms/images). Fixture + tests.
3. **mercado_unico enabled=True:** discovery por homepage (listado SPA
   vacío); parser NUXT/og validado. Fixture + tests. Algunos avisos traen
   `precio: null` en el portal — no es bug del parser.
4. robots reconfirmados: MP 404 (sin restricción), MU Allow:/.
5. **No se tocó** zonaprop/argenprop/mercadolibre/properati.

**Validado**

- Parsers contra HTML real (curl 200) para ambas fuentes.
- `py_compile` de módulos tocados.
- Tests nuevos de parser + extracción de links.

**Archivos:** `queries.py`, `links.py`, `selectors.py`,
`parsers/mercado_unico.py` (zone), `render.yaml`, `docs/CRON_EXTERNO.md`,
`docs/FUENTES_CANDIDATAS.md`, fixtures/tests, `PROGRESS_LOG.md`.

---

## 2026-09-15 — Encargo #2: InmoUp, antigüedad 60d, priority_score, volumen, fuentes

**Qué se hizo**

1. Investigación de portales por provincia → `docs/FUENTES_CANDIDATAS.md`
   (tablas BA/CBA/SF/MZA). Solo **2 fuentes habilitables** sin anti-bot:
   `cordobaprop` (ya live) e `inmoup` (nuevo).
2. **InmoUp** integrado de punta a punta: `parsers/inmoup.py` (JSON-LD),
   `queries.inmoup_list_urls`, `links._inmoup`, `SourceConfig enabled=True`,
   fixture real + test.
3. `MAX_AGE_DAYS = 60` (antes 90); test de 65 días agregado.
4. `Property.priority_score` + `compute_priority_score` (recencia, precio
   vs mediana, 2–3 amb, fotos). Default `ORDER BY priority_score DESC` en
   `GET /properties`.
5. Volumen: `MAX_DETAILS_PER_SOURCE=80`, `MAX_LIST_PAGES=5`, delay 1.0.
6. Cron semanal crawler documentado en `render.yaml` (comentado: plan
   Render). Motivo 7 días: ~8–9 pases antes de expirar a 60d.

**Fuentes evaluadas y descartadas — no reintentar sin novedad**

- ZonaProp / Argenprop / ML / Properati: challenge o 403 de borde.
- Propia (Santa Fe): HTML 200 pero Nuxt SPA sin hrefs de ficha.
- MendozaProp / Mercado Único: sin links estáticos en listado.
- Roomix/BuscadorProp: meta/agregadores, bajo valor o ToS.

**Qué se validó**

- `pytest` (ver README_ENTREGA): tests previos + inmoup + priority +
  expiry 65d.
- Corrida live completa de crawler **no medida end-to-end** en este
  entorno (tiempo de red hacia portales + dyno); InmoUp list+detail
  verificados manualmente con curl 200.

**Datos existentes:** `priority_score` se agrega con default 0; filas
viejas quedan en 0 hasta el próximo upsert. `hidden_at` sin cambio de
semántica (solo el umbral bajó a 60).

**Variables de entorno:** sin nuevas obligatorias. Crons externos:
`API_URL` + `ADMIN_KEY`.

**Archivos tocados:** crawler (runner, normalize, queries, links,
selectors, parsers/inmoup), main.py, render.yaml, tests, fixtures,
docs/FUENTES_CANDIDATAS.md, PROGRESS_LOG.md.

---

## 2026-09-15 — Encargo one-pass (Grok): antigüedad, cursores, limpieza debug, ZonaProp bloqueado

**Qué se hizo**

1. **Tarea 1:** eliminados endpoints de debug
   `POST /admin/debug/create-test-agency`,
   `GET /admin/debug/agency-by-id/{id}` y el modelo `DebugCreateAgencyIn`.
2. **Tarea 2:** `Property.hidden_at`; `expire_stale_properties`;
   `POST /admin/properties/expire-stale`; `GET /properties` y detail
   filtran ocultas (admin + `include_hidden=true` puede verlas).
   Antigüedad efectiva = `origin_published_at` si es ISO parseable, si no
   `detected_at`. Upsert del crawler resetea `hidden_at` si el aviso
   reaparece.
3. **Tarea 3 (ZonaProp):** `queries.py` → solo Caballito/venta páginas
   1–5; `links.py` → solo `/propiedades/*-ubicado-en-*`; fixture + test
   de parser. **No se habilitó:** listados/fichas devuelven Cloudflare
   challenge (403). `enabled=False` y nota en `selectors.py`.
4. **Tarea 4:** tabla `CrawlCursor`; runner avanza/reinicia página;
   `MAX_DETAILS_PER_SOURCE = 40`. Crons documentados comentados en
   `render.yaml`.
5. **Tarea 5:** checklist abajo.
6. **Tarea 6:** regeneradas secc. 3, 4, 7, 8, 10 de `PLAN_MAESTRO.md`;
   documentada reversión 6.2.1 (Google opcional).

**Qué se validó (corrido de verdad)**

- `pytest apps/api/tests/` → **40/40 pasan** (30 previos + expiry +
  cursor + zonaprop parser fixture).
- `grep -rn "admin/debug" apps/` → vacío.
- `npm run build` **no se corrió** (sin toolchain Node en este entorno;
  no se tocó frontend).

**Datos existentes:** columnas nuevas vía `ensure_schema_columns` /
`create_all` de tablas nuevas. Filas viejas: `hidden_at = NULL`
(siguen visibles hasta el primer expire). `CrawlCursor` arranca vacío.

**Variables de entorno nuevas:** ninguna obligatoria nueva. Ya existentes
a cargar en Render si faltan: `ADMIN_KEY`, y para crons externos
`API_URL` + `ADMIN_KEY`. Lemon Squeezy / Vonage sin cambios de schema.

**Pendiente**

- Decisión de producto sobre piloto Caballito vs Cloudflare ZonaProp.
- Activar crons (plan Render o cron-job.org).
- Habilitar ZonaProp solo si deja de devolver challenge.

**Archivos tocados:** `apps/api/app/main.py`, `crawler/runner.py`,
`crawler/queries.py`, `crawler/links.py`, `crawler/selectors.py`,
`render.yaml`, `tests/test_property_expiry.py`,
`tests/test_crawl_cursor.py`, `tests/test_zonaprop_parser.py`,
`tests/fixtures/zonaprop_detail.html`, `docs/PLAN_MAESTRO.md`,
`PROGRESS_LOG.md`.

---

## 2026-09-15 — Auditoría de estado real del repo (sin cambios de código)

**Qué se hizo:** se clonó `main` completo y se comparó contra
`docs/PLAN_MAESTRO.md` y contra este mismo log. Motivo: tanto el documento
maestro como este archivo habían quedado atrasados respecto del código —
el log se cortaba en "Etapa 4 parte 1" (2026-09-13) y desde ahí hubo ~20
commits que cerraron las etapas 5 a 9. Esta entrada y las tres siguientes
reconstruyen ese tramo faltante para que cualquier sesión nueva lea el
estado verdadero y no uno de hace dos días.

**Verificado en este entorno (no declarado — corrido de verdad):**

- `pytest apps/api/tests/` → **30/30 pasan** (no 8 como decía el plan
  maestro): `test_security.py`, `test_subscriptions_credits.py`,
  `test_t87_listing_group_reveal.py`.
- Inventario real: **56 endpoints** en `apps/api/app/main.py` (3508 líneas)
  y **17 tablas** SQLAlchemy.
- No se pudo correr `npm run build` en este entorno (sin toolchain de
  Node disponible) — sigue valiendo la regla de `CLAUDE.md`: la primera
  corrida real del front es el build de Vercel.

**Desfasajes encontrados entre `docs/PLAN_MAESTRO.md` y el código real.**
El plan maestro afirma que estas cosas "no existen"; todas existen hoy:

| Afirmación del plan maestro | Realidad en `main` al 2026-09-15 |
|---|---|
| Secc. 7: "el crawler no existe todavía" | Existe `apps/api/app/crawler/` completo (runner de 2 etapas, 7 parsers, dedup, normalize, links, selectors) |
| Secc. 3.4: "no hay suscripciones/planes" | Tablas `Subscription` + `LeadCredit`, `PLAN_30/50/99` con cupo 30/60/ilimitado |
| Secc. 3.4: "PaymentGateway es un mock que deniega" | Lemon Squeezy real con checkout hosteado + webhook con verificación HMAC |
| Secc. 3.4: "no hay panel de revisión manual" | Backend + pantalla `/admin` en el front |
| Secc. 4.2: `AgencyPhone`, `Property.images`, `origin_published_at`, `verification_status` pendientes | Los cuatro implementados, con migración de `image` → `images` |
| Secc. 10 etapa 9: subdominios "al final, no bloquea nada" | Ya hecho: `middleware.ts` + `/tienda/[slug]` + `GET /agencies/by-slug/{slug}` |

**Acción pendiente derivada:** regenerar `docs/PLAN_MAESTRO.md` para que
deje de contradecir al código. Mientras no se haga, **este archivo manda
sobre el plan maestro en todo lo que sea "estado actual"**; el plan maestro
sigue siendo la fuente de verdad solo para *reglas de negocio* (secc. 5) y
*decisiones de producto* (secc. 6), que no cambiaron.

---

## 2026-09-15 — Deuda abierta detectada en la auditoría (4 ítems, priorizados)

Ninguno de estos es un bug que rompa lo que ya funciona; son huecos entre
lo que el código hace y lo que el plan maestro exige.

**1. Endpoints de debug vivos en `main` (borrar ya).** Los commits
`4eaa279` y `0a06ad5` agregaron `POST /admin/debug/create-test-agency` y
`GET /admin/debug/agency-by-id/{id}`, ambos con docstring "DEBUG TEMPORAL —
borrar después de resolver el test de Lemon Squeezy (tarea 5)". Esa tarea
ya se resolvió. Están detrás de `require_admin`, así que no hay fuga
abierta, pero `create-test-agency` crea una `Agency` con
`verification_status="VERIFIED"` directo, salteando toda la cola de
revisión manual de la Etapa 4. Eliminar los dos endpoints y el modelo
`DebugCreateAgencyIn`.

**2. Falta el proceso periódico de antigüedad (plan maestro secc. 7).**
`MAX_AGE_DAYS = 90` existe en `crawler/runner.py` pero es **solo filtro de
entrada**. El plan maestro pide explícitamente un cron que oculte las
propiedades al cumplir el límite mientras siguen publicadas en Propomi —
eso no existe. Tampoco hay scheduler de ningún tipo: `render.yaml` define
únicamente el servicio web, y `POST /admin/crawler/run` es disparo manual
con `X-Admin-Key`. Sin esto, una propiedad indexada hace 55 días se queda
publicada para siempre.

**3. El crawler funciona pero casi no tiene fuentes habilitadas.** Estado
confirmado de robots.txt al 2026-09-15 (documentado en `selectors.py`):

- `cordobaprop` → **`enabled=True`**, única fuente viva. Robots permisivo.
- `zonaprop` → `enabled=False`. El robots.txt **sí permite** fichas
  (`/propiedades/*-ubicado-en-*`) y páginas de listado 2 a 5. El bloqueante
  ya no es robots sino la **tarea 13**: validar `queries.py`/`links.py`
  contra esas reglas de URL/paginación antes de habilitar.
- `mendozaprop` → `enabled=False`. No publica robots.txt (404 real) → sin
  restricciones declaradas. También esperando tarea 13.
- `mercado_unico` → `enabled=False`. `Allow: /` general. Esperando tarea 13.
- `argenprop`, `mercadolibre`, `properati` → **403 en el borde**
  (CloudFront / bot protection propia / AWS ELB). Ni el robots.txt se
  puede leer con curl simple. Sin proxy anti-bot dedicado no son viables.

**Conflicto de producto que esto abre (decisión del dueño, no técnica):**
el plan maestro fija como zona piloto **Caballito, CABA** con ZonaProp +
Argenprop. Hoy Argenprop está fuera de alcance y la única fuente viva es
CordobaProp, que no cubre CABA. Las opciones son: (a) mover el piloto a
Córdoba, (b) habilitar ZonaProp vía tarea 13 y hacer el piloto solo con esa
fuente, o (c) invertir en solución anti-bot. **Recomendado: (b), con (a)
como plan B** — ZonaProp solo ya cubre Caballito con volumen suficiente, y
no requiere gasto nuevo.

**4. Volumen de crawl por corrida demasiado chico para llenar catálogo.**
`MAX_LIST_PAGES_PER_SOURCE = 3`, `MAX_DETAILS_PER_SOURCE = 15`,
`REQUEST_DELAY_SECONDS = 1.0`. Son ~15 fichas por fuente por corrida, y
como no hay cursor persistido, cada corrida reempieza desde la página 1 y
vuelve a traer casi lo mismo. Para un piloto real hace falta paginación con
estado.

---

## 2026-09-14/15 — Etapa 8: crawler real (reconstrucción del tramo no logueado)

Cubre los commits `29fb925`, `3bbea0e`, `9574db4`, `078997a`, `0715a87`,
`d1fde0a`.

- **Arquitectura de 2 etapas** (`crawler/runner.py`): etapa 1 genera URLs
  de listado desde `selectors.SOURCES[...].list_urls_fn` y extrae de su
  HTML las URLs de ficha (`links.py`); etapa 2 baja cada ficha, la parsea
  con el parser específico de la fuente, normaliza y hace upsert contra
  `Property`. Nunca entra detrás de login, nunca hardcodea credenciales,
  nunca crawlea fuentes con `enabled=False`.
- **7 parsers** en `crawler/parsers/`: zonaprop, argenprop, cordobaprop,
  mendozaprop, mercado_unico, mercadolibre, properati. Todos basados en
  extraer el **JSON embebido** en el HTML, no en selectores CSS frágiles —
  esto resuelve el riesgo que el plan maestro marcaba en la secc. 12
  ("selectores del scraper sin verificar").
- **Dedup** (`crawler/dedup.py`): fingerprint de
  `zona | dirección normalizada | precio bucketeado a 5000 | superficie
  bucketeada a 5 | ambientes`. Pensado para fusionar el mismo aviso
  publicado en más de un portal, no solo repetidos dentro de una fuente.
  Coherente con el plan maestro: marca candidatos para **revisión manual**
  (`GET /properties/review-queue`, `POST /properties/{id}/review`), no
  fusiona automáticamente.
- **Regla no negociable #3 respetada:** `normalize.strip_description()`
  reusa `strip_contact_leaks` de `main.py` sobre la descripción scrapeada,
  además de la pasada que ya hace `base.strip_contact_leaks` al extraer del
  HTML. Doble pasada deliberada.
- **Bugs encontrados y corregidos en el camino** (valen como aprendizaje,
  no repetirlos):
  - `links.py`: el patrón de URL de CordobaProp era incorrecto; el real es
    `/propiedad/<id>-<slug>`.
  - `cordobaprop_list_urls`: necesitaba `viewtype=list` y paginación por
    offset, no por número de página.
  - **Mojibake:** `requests` cae al default HTTP (ISO-8859-1) cuando el
    servidor no declara charset en `Content-Type`. Estos portales sirven
    UTF-8 real sin declararlo → "CÃ³rdoba" en vez de "Córdoba" en
    `Property.zone`. Corregido forzando `apparent_encoding` en `_get()`.
  - El upsert congelaba `zone`/`city`/`type` de la primera detección y no
    los actualizaba en corridas posteriores.
- **Búsqueda del front adaptada** (`f226ada`, `dbca137`): nuevo
  `GET /properties/filters` para autodetectar ciudad/zona desde el catálogo
  real, y la barra de búsqueda pasó a grid de 5 campos (ciudad + zona).

---

## 2026-09-14 — Etapas 5 a 7 y 9: monetización real, identidad, cold start, subdominios

Cubre el commit `f5439d5` ("tandas 2-6") y los fixes posteriores de OTP.
Este tramo nunca se logueó en su momento; se reconstruye acá desde el
código.

**Etapa 5 — Monetización completa (Lemon Squeezy).**

- Tablas `Subscription` (plan activo, cupo del ciclo, consumido,
  renovación) y `LeadCredit`, ambas por agencia.
- `PLAN_CUPO`: `PLAN_30` → 30 reveals, `PLAN_50` → 60 reveals, `PLAN_99` →
  ilimitado, `PAY_PER_LEAD` → 0. Coherente con decisión 6.2.3 del plan
  maestro: **lo que consume cupo es un reveal, no una oferta recibida**.
- Orden de consumo en `reveal_contact`: primero `free_leads_remaining` (los
  10 gratis al verificarse), después cupo de plan, después pay-per-lead a
  USD 5. Así no se pisan entre sí, como exige la secc. 8.
- Excedente dentro del ciclo → se permite seguir revelando a pay-per-lead
  en vez de bloquear (decisión 6.2.4).
- `POST /payments/checkout` crea checkout hosteado de Lemon Squeezy;
  `POST /payments/webhooks/lemonsqueezy` verifica `X-Signature` (HMAC-SHA256
  del body crudo) y solo actúa con `order_created` + `status == paid`.
  Mapeo variant→plan por variables de entorno (`LS_VARIANT_PLAN_BASIC/PRO/
  PREMIUM`), con compatibilidad hacia los nombres legacy.
- `docs/LEMON_SQUEEZY_CHECKLIST.md`: pasos operativos para cuando aprueben
  la cuenta. **No hace falta código nuevo** — solo cargar `STORE_ID`,
  `VARIANT_ID`, API key y `LEMON_SQUEEZY_WEBHOOK_SECRET` en Render.
- Tests: `test_subscriptions_credits.py` cubre este flujo.
- `reveal_contact` sigue bloqueando con 403 si
  `verification_status != "VERIFIED"` (decisión 6.2.2).

**Etapa 2 revisada — identidad del comprador.**

- `7de1dff`: **se eliminó la exigencia de Google.** El SMS verificado
  alcanza como verificación de comprador; Google quedó opcional. Esto
  revierte parcialmente la decisión 6.2.1 del plan maestro (que pedía
  ambos) — se cambió porque el doble gate mataba la conversión al final del
  wizard, que es exactamente lo que el diseño de 3 pantallas busca evitar.
- SMS real conectado: `sms_vonage.py` + selector `OTP_SMS_PROVIDER`
  (`f5f4732`). Fixes de normalización AR: se quita el 9 del prefijo al
  enviar a Vonage porque lo rechazaba como `AR-UNKNOWN` (`682687f`), y
  `VONAGE_KEEP_AR_NINE` para matchear la whitelist de números de test en
  modo demo (`eb81fe1`). Log de diagnóstico cuando `normalize_phone`
  rechaza (`2d79d7e`).
- `IntentWizard.tsx` (333 líneas) convive con `OfferModal.tsx`. Fixes:
  auto-recuperación de sesión huérfana ante 403 de celular (`f4b7f79`),
  `property_id` faltante al crear `IntentProfile` en `/intents` (`756dcb9`),
  hint y validación E.164 en el campo Celular (`29663ff`).

**Etapa 3 cerrada — `search_performed`.** `POST /events/search_performed` +
`GET /analytics/demand` + `GET /agencies/{id}/market-opportunities`, con
pestaña "Demanda" (`DemandPanel.tsx`) en el dashboard de agencia. Guardado
agregado y anónimo, nunca atado a un comprador identificable.

**Etapa 6 — Cold start.** Tabla `ColdStartTask`, cola en
`GET /admin/cold-start/pending`, `POST /admin/cold-start/{id}/mark-sent`
(envío 100% manual por ahora, como preveía la secc. 9), y flujo de reclamo
por token: `GET /onboarding/{token}`, `POST /onboarding/{token}/complete`,
`POST /agencies/{id}/claim`, con pantalla
`apps/web/app/onboarding/[token]/page.tsx`.

**Etapa 7 — Ingesta manual.** `POST /properties/ingest` y `POST /properties`
para agentes ya verificados.

**Etapa 9 — Subdominios por agencia.** `apps/web/middleware.ts` detecta el
subdominio, `GET /agencies/by-slug/{slug}` resuelve la agencia, y
`apps/web/app/tienda/[slug]/page.tsx` renderiza el portal propio **con el
mismo funnel de oferta → reveal pago corriendo adentro**, no una versión
reducida. DNS wildcard documentado en `apps/web/docs-wildcard-dns.md`.

**Fuera de roadmap, construido igual:** modelo `Lead` con su propio reveal
(`POST /leads`, `GET /leads`, `POST /leads/{id}/reveal`), grupos de listings
duplicados (`GET /properties/{id}/group`, con
`test_t87_listing_group_reveal.py` cubriendo el reveal sobre un grupo), y
`AgentLeadActions.tsx` en el front.

---
## 2026-09-13 — Cierre de sesión / punto de retomada

- **Este es un corte de sesión de chat, no una etapa nueva.** El usuario va
  a continuar en una sesión distinta de Claude.ai. Todo lo relevante ya
  está pusheado en `main` — no hay nada "en el aire" sin guardar.
- **Estado real confirmado al cierre:** Etapas 1, 2 y 3 del roadmap
  (sección 10) cerradas de punta a punta. Etapa 4 (panel de revisión
  manual de agencias) con la **parte 1 (backend) ya pusheada**
  (`main.py` v6: `ADMIN_KEY`, `require_admin`,
  `GET /admin/agencies/pending`, `POST /admin/agencies/{id}/approve`,
  `POST /admin/agencies/{id}/reject`).
- **Próximo paso exacto, sin ambigüedad:** Etapa 4 **parte 2 (frontend)** —
  pantalla interna nueva en `apps/web` (ej. ruta `/admin`) que:
  1. Pida la clave (`X-Admin-Key`) una sola vez y la guarde en memoria de
     sesión del navegador (no en `localStorage` persistente — es una
     clave de administración, no una sesión de usuario común).
  2. Liste la cola de `GET /admin/agencies/pending` (ya ordenada por
     prioridad desde el backend).
  3. Tenga botones de aprobar/rechazar por agencia, con campo opcional de
     notas, llamando a `POST /admin/agencies/{id}/approve` o `/reject`.
- **Pendiente recordatorio operativo (no de código):** cargar `ADMIN_KEY`
  en el Environment Group de Render con un valor random antes de usar el
  panel en producción real — todavía no confirmado si el usuario ya lo
  hizo.
- **Cómo debe arrancar la próxima sesión:** con la frase de arranque
  estándar ya definida en `CLAUDE.md` ("Acá está el repo, seguí las
  instrucciones" o equivalente) alcanza — la sesión nueva lee `CLAUDE.md`
  (v7) + este archivo, entiende que el próximo paso es la Etapa 4 parte 2,
  y arranca directo a construirla sin preguntar qué hacer (regla v7) y sin
  re-preguntar nada de lo ya fijado (rutas, PowerShell, versionado, trabajo
  en partes chicas, etc.).
- No hubo cambios de código en esta entrada — es puramente de cierre/traspaso.

---

## 2026-09-13 — Etapa 4 parte 1: backend del panel de revisión manual de agencias

- **Objetivo (roadmap sección 10, punto 4):** panel interno mínimo viable
  para aprobar/rechazar agencias pendientes de verificación, protegido por
  clave fija, ordenado por prioridad de suscripción. Esta parte es **solo
  backend** — el frontend (la pantalla en sí) queda para la próxima entrega,
  siguiendo la sugerencia explícita de `CLAUDE.md` de partir esta etapa en
  back-end primero y funcionando solo, front-end después.
- **Archivo pusheado:** `apps/api/app/main.py` → versión **v6**.
- **Nueva variable de entorno `ADMIN_KEY`:** mismo patrón de seguridad que
  `JWT_SECRET` — si `ENV=production` y no está seteada, el proceso no
  arranca (falla rápido en vez de correr insegura). En desarrollo tiene un
  default (`dev-only-admin-key`). **Falta cargarla en Render** con un valor
  random antes de que el panel se use en producción real.
- **Nueva dependencia `require_admin`:** valida un header `X-Admin-Key`
  (nunca query param, para que la clave no quede en logs de acceso ni en el
  historial del navegador) contra `ADMIN_KEY` con `secrets.compare_digest`
  (comparación segura contra timing attacks, mismo patrón ya usado para
  comparar códigos OTP).
- **3 endpoints nuevos, todos protegidos por `require_admin`:**
  - `GET /admin/agencies/pending`: lista agencias con
    `verification_status == PENDING`, ordenadas por `verification_priority`
    descendente (doc 6.2 — quien ya se suscribió antes de verificarse pasa
    primero).
  - `POST /admin/agencies/{id}/approve`: pasa a `VERIFIED`, sincroniza el
    booleano `verified` (deprecated) por compatibilidad hacia atrás, y
    otorga los `FREE_LEADS_ON_VERIFICATION` (10 leads gratis) si todavía no
    los tenía cargados.
  - `POST /admin/agencies/{id}/reject`: pasa a `REJECTED`.
  - Ambos de aprobar/rechazar aceptan `notes` opcional, pasado siempre por
    `sanitize_free_text()` (regla no negociable de la sección 5 — ningún
    campo de texto libre nuevo se guarda sin pasar por ahí, ni siquiera en
    el panel interno).
- **No se tocó:** ningún endpoint ni modelo existente — solo se agregaron
  la constante, la dependencia y los 3 endpoints nuevos al final del
  archivo.
- **Validado en este entorno (Claude):** `python3 -m py_compile` sin
  errores. Mismo alcance que entregas anteriores (sin `pytest` local
  disponible) — recomendable sumar tests para estos 3 endpoints cuando se
  pueda correr `pytest` real, no se escribieron todavía.
- **Pendiente / próximo paso (parte 2, sin preguntar según regla v7):**
  pantalla interna en `apps/web` (ruta nueva, ej. `/admin`) que pida la
  clave una vez, la guarde en memoria de sesión del navegador, liste la
  cola de `GET /admin/agencies/pending` y tenga botones de aprobar/rechazar
  — siguiente entrega.
- Archivos tocados: `apps/api/app/main.py` (v6), `PROGRESS_LOG.md` (v11 —
  este mismo archivo).

---

## 2026-09-13 — Etapa 3 v4: pestaña "Demanda" integrada al dashboard de agencia

- **Cierra la Etapa 3 de punta a punta:** search_performed se guarda (v1) →
  se lee agregado en el backend (v2) → hay tipos + fetch en el frontend
  (v3) → ahora se ve en pantalla, dentro del dashboard real de agencia (v4).
- **`apps/web/components/DemandPanel.tsx` → v2** (reemplaza la v1 pusheada
  antes, que nunca llegó a integrarse): reescrito con estilos inline en vez
  de clases Tailwind — al ver `AgentDashboard.tsx` real se confirmó que el
  proyecto usa clases CSS propias (`agentdashpane`, `tab`, `muted small`,
  etc. de `globals.css`), no Tailwind. Los estilos inline evitan depender
  de clases que no se pudieron verificar sin ver `globals.css`.
- **`apps/web/components/AgentDashboard.tsx` → v2:**
  - Nueva pestaña "Demanda" (ícono `TrendingUp` de lucide-react) entre
    "Oportunidades" y "Mi cuenta".
  - `section` ahora admite `'demanda'` además de los valores existentes.
  - El pane nuevo simplemente renderiza `<DemandPanel session={session}/>`
    — el fetch a `/analytics/demand` lo hace el propio componente, no
    `AgentDashboard` (mismo patrón de autonomía que ya usan otros paneles).
  - No se tocó ninguna otra pestaña, estado ni función existente.
- **Validado en este entorno (Claude):** conteo de balance de `{}` y `()`
  en ambos archivos → coincide. **No se pudo correr `npx tsc --noEmit` ni
  `npm run build` real** (sin entorno de test disponible, ver `CLAUDE.md`)
  — primera corrida real en el build de Vercel.
- **Pendiente / no se tocó en esta etapa:**
  - No se vio `globals.css` — si el look del panel nuevo desentona mucho
    visualmente con el resto (colores, tipografía), es candidato a un
    ajuste chico una vez visto en Vercel.
  - El umbral fijo de `avgResultCount < 3` para mostrar el mensaje de "poca
    oferta" es arbitrario (no viene del plan maestro) — ajustable si en la
    práctica no resulta útil.
- **Archivos tocados:** `apps/web/components/DemandPanel.tsx` (v2),
  `apps/web/components/AgentDashboard.tsx` (v2), `PROGRESS_LOG.md` (v10 —
  este mismo archivo).
- **Próximo paso (decidido sin preguntar, según regla v7 de `CLAUDE.md`):**
  revisar `docs/PLAN_MAESTRO.md` sección 10 para confirmar cuál es la
  siguiente etapa numerada del roadmap que sigue sin cerrar, y arrancarla
  directo en la próxima entrega.

---

## 2026-09-13 — Etapa 3 v2: endpoint `GET /analytics/demand`

- **Objetivo:** cerrar el ciclo de la v1 de esta etapa — ahora hay una forma
  de LEER lo que `search_performed` viene guardando desde `GET /properties`.
- **Archivo pusheado:** `apps/api/app/main.py` → versión **v5**.
- **Nuevo endpoint `GET /analytics/demand`** (requiere sesión de agente,
  mismo guard `require_agent` que `/analytics/summary`):
  - Toma los últimos `limit` eventos `search_performed` (query param,
    default 500, para no recorrer toda la tabla a medida que crezca — no
    hay todavía una tabla de agregación propia, se calcula al vuelo).
  - Devuelve `topZones`, `topTypes`, `topOperations` (rankings por cantidad
    de búsquedas que usaron ese filtro) y `avgResultCount` (promedio de
    resultados devueltos por búsqueda, útil para detectar filtros
    demasiado restrictivos con poca oferta real).
  - Es agregado y anónimo por diseño: nunca devuelve `user_id` ni datos de
    una búsqueda puntual, solo conteos totales.
- **No se tocó:** `GET /properties`, `ALLOWED_EVENTS`, ni ningún otro
  endpoint — cambio acotado a agregar este endpoint nuevo al final del
  archivo, después de `/analytics/summary`.
- **Validado en este entorno (Claude):** `python3 -m py_compile` sin
  errores. Mismo alcance de verificación que la v1 (sin `pytest` local
  disponible) — primera corrida real en Render.
- **Pendiente / no se tocó en esta etapa:**
  - No hay UI en el frontend todavía que consuma este endpoint (ej. un
    panel "Demanda" dentro de `/agencia`) — es un pedacito de backend
    puro, a propósito, para no mezclar back+front en la misma entrega.
  - Si en el futuro el volumen de `search_performed` crece mucho, este
    endpoint recorre solo los últimos `limit` — no hay paginación ni
    agregación pre-calculada (tabla de rollup) todavía; no hace falta
    hasta que el volumen real lo justifique.
- **Próxima etapa a encarar:** a definir con el usuario — candidatos:
  (a) UI de "Demanda" en el dashboard de agencia consumiendo este
  endpoint, o (b) seguir avanzando otro punto de la fase Intelligence /
  otra fase del roadmap.
- Archivos tocados: `apps/api/app/main.py` (v5), `PROGRESS_LOG.md` (v9 —
  este mismo archivo).

---

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

## Pendientes sueltos detectados (sesión del 13/09/2026)

**Encoding roto (bug preexistente, no introducido por nosotros):**
- `components/OfferModal.tsx` tiene varios strings con acentos corrompidos: `Ã©`, `â€“`, `MÃ¡s`, `dÃ­as`, `FinanciaciÃ³n` en vez de é/–/Más/días/Financiación. Se ve mal en producción tal cual está. Pendiente: pasada de limpieza de encoding en ese archivo (mismo tipo de problema que tuvimos al editar `ComparePanel.tsx` con PowerShell — usar `-Encoding UTF8` explícito al tocarlo).
- Antes de tocar más archivos con `-replace`/`Set-Content` en PowerShell, siempre especificar `-Encoding UTF8` tanto al leer como al escribir, para no repetir el problema que tuvimos con `ComparePanel.tsx` (corrompió "Actualización" y luego el guión largo `—`).

**Google login — ya existe código parcial en el frontend (descubierto sin buscarlo):**
- `lib/google.ts` existe y exporta `renderGoogleButton`.
- `lib/api.ts` ya tiene `linkGoogleIdentity`, `requestOtp`, `verifyOtpBuyer`, `setBuyerSession`.
- `components/OfferModal.tsx` ya importa y usa `renderGoogleButton` y el flujo de OTP para el comprador dentro del modal de oferta.
- **Implicancia importante para cuando retomemos el tema de Clerk:** puede que ya haya un login con Google implementado "a mano" (sin Clerk) en el flujo de oferta, y/o un OTP de comprador ya conectado a `withIdentity` que no vimos completo todavía. Antes de meter Clerk hay que leer `OfferModal.tsx` completo y `lib/google.ts` para saber qué existe ya, qué falta, y si conviene usar eso en vez de agregar Clerk.
- También pendiente: confirmar si `BuyerIdentityModal` (el que dispara `withIdentity` en `page.tsx`) es el mismo flujo que el de `OfferModal.tsx`, o si son dos gates de identidad distintos y separados (posible inconsistencia a revisar).

**Falla de fondo en medición de demanda (detectada en esta sesión, ver conversación):**
- Hoy `BuyerIdentityModal` pedía nombre+celular autodeclarados sin verificar como gate de "identidad" — dato de baja confiabilidad para medir demanda real. Pendiente evaluar si ya está resuelto por el OTP que aparece en `OfferModal.tsx`, o si sigue siendo el gate viejo.
