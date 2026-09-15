# 0. Cómo leer este documento

Este documento asume que quien lo lee **no sabe nada del proyecto**.
Está escrito para que una persona o una IA de desarrollo pueda tomarlo y
construir el producto completo sin necesitar contexto adicional, salvo
el código fuente real que se adjunta aparte (el repo Git).

Estructura:

1.  Qué es Propomi y por qué existe (modelo de negocio)
2.  Roles y flujos de usuario, explicados paso a paso
3.  Estado real del código HOY --- qué está construido y probado, qué es
    demo/mock, qué no existe
4.  Modelo de datos completo (el actual + el que falta agregar)
5.  Reglas de negocio no negociables (privacidad, anti-fuga de contacto)
6.  Decisiones de producto --- cuáles ya están tomadas y cuáles son
    defaults recomendados a confirmar
7.  El crawler (estado real, fuentes, antigüedad, cursores)
8.  Sistema de monetización --- estado real
9.  Cold start --- cómo arrancar sin usuarios
10. Roadmap completo, en orden de dependencia
11. Cómo entregar el trabajo (checklist de calidad antes de cada
    entrega)
12. Problemas conocidos en el repo actual que hay que arreglar

# 1. Qué es Propomi

Propomi (nombres usados en distintas etapas del proyecto: OMI / Proferta
/ uniprop.ar / Propomi --- todavía sin nombre de marca final decidido)
es un **portal inmobiliario para Argentina/LATAM**, enfocado solo en
**venta** (no alquileres), que se diferencia de portales tradicionales
(ZonaProp, Argenprop, Properati) en el modelo de monetización:

-   Los portales tradicionales cobran a la inmobiliaria **por publicar**
    la propiedad.
-   Propomi **no cobra por publicar.** Agrega propiedades vía crawler
    (scraping de otros portales) de forma gratuita para la inmobiliaria,
    y cobra recién cuando hay un **comprador real con intención
    concreta** (una oferta de precio) y la inmobiliaria decide **revelar
    el contacto** de ese comprador.

Mecanismo central: **oferta → contraoferta → reveal de contacto pago.**

1.  Un comprador ve una propiedad y en vez de "escribir un mensaje",
    completa un flujo estructurado (sin campos de texto libre) donde
    propone un precio, indica capital disponible, forma de pago, plazo y
    condiciones.
2.  Esa oferta llega a la inmobiliaria **sin el nombre ni el teléfono
    del comprador** --- el contacto está oculto.
3.  La inmobiliaria puede aceptar, rechazar o contraofertar usando
    **botones estructurados**, nunca texto libre (para que no pueda
    filtrar su propio contacto y saltear el pago).
4.  Si la inmobiliaria quiere el contacto real del comprador, tiene que
    **pagar** (por lead individual, o consumir cupo de una suscripción).
    Recién ahí se le muestra nombre, teléfono y email del comprador.

### Precedente estudiado

Properati (Argentina) usó un modelo parecido pero nunca fue rentable por
sí sola, terminó vendida dos veces. La diferencia clave que se apunta a
favor de Propomi: el crawler resuelve el problema de oferta de
propiedades sin depender de que las inmobiliarias suban nada manualmente
--- Properati sí dependía de eso.

### Zona piloto

**Caballito, CABA** --- elegida por buen volumen (\~7.800 propiedades),
alta rotación real, y menos competencia que Palermo.

### Fuentes de datos previstas para el crawler

ZonaProp + Argenprop para el piloto. Remax a nivel nacional. Santa Fe
tiene un portal regional propio ("Propia", de COCIR); Córdoba tiene
"CordobaProp" (CPI); Entre Ríos no tiene un portal regional identificado
todavía.

# 2. Roles y flujos de usuario

Hay dos roles: **Comprador** y **Agente** (persona de una
inmobiliaria/agencia).

## 2.1 Comprador

El comprador **nunca necesita crear una cuenta con contraseña**. Navega
anónimo (sesión "invitado", generada automáticamente) hasta el momento
en que decide ofertar.

Flujo diseñado (y ya construido) para minimizar el abandono, aplicando
principios de comportamiento (compromiso psicológico progresivo, "sunk
cost"):

1.  Explora propiedades, filtra, guarda favoritas, compara.
2.  Entra a proponer un precio sobre una propiedad puntual. Se abre un
    flujo de **3 pantallas** (deliberadamente NO son 7 pasos separados
    --- ver nota de diseño más abajo):
    -   **Pantalla 1 --- "Tu oferta":** dos sliders juntos: cuánto
        quiere ofertar (con atajos de -5%/-10%/-15% sobre el precio de
        lista, más un slider fino) y con cuánto capital disponible
        cuenta (en escalones de USD 30.000, de 30.000 a 150.000+).
    -   **Pantalla 2 --- "Preferencias":** todo con botones de un solo
        toque, sin texto libre: forma de pago (Contado / Financiación /
        Mixta), plazo (0-30 / 30-60 / 60-90 / +90 días), condiciones de
        compra (chips multi-selección: "Mudanza rápida", "Tengo otra
        propiedad para entregar/vender", "Busco financiación bancaria",
        "Sin condicionantes particulares"). Estas condiciones
        seleccionadas se concatenan automáticamente en un campo de
        comentario --- **el comprador nunca escribe texto libre**, así
        se evita que filtre sin querer su propio teléfono o su nombre
        completo antes de tiempo.
    -   **Pantalla 3 --- "Contacto":** arriba se muestra un resumen tipo
        chip (ej. "USD 112.000 · Mixta · 30-60 días") para que sienta
        que ya cerró la negociación y solo falta dejar sus datos. Pide
        nombre, celular y email (opcional). Incluye un mensaje explícito
        de que sus datos quedan protegidos por seguridad y nunca se usan
        para spam ni se comparten fuera de este flujo.
3.  Al enviar, la oferta queda guardada con el contacto **oculto**
    (`contact_revealed = false`) hasta que la agencia decida revelarlo
    (pagando o con cupo de suscripción).

### Nota de diseño: por qué 3 pantallas y no 7

La primera versión de este flujo tenía 7 pasos separados (precio,
capital, forma de pago, plazo, condiciones, contacto, confirmación). Se
descartó explícitamente por un motivo de comportamiento humano: **una
persona buscando comprar una casa no va a completar un formulario de 7
pasos.** El diseño correcto agrupa por lógica psicológica: primero los
números (donde la persona quiere sentir control fino, con sliders),
después las preferencias rápidas (todo tocable sin pensar), y al final
solo el contacto --- sin pantalla de "revisión" separada, porque eso
vuelve a bajar el ritmo. Los indicadores de progreso son puntos pequeños
y discretos, no números de "paso X de Y", para que el avance se sienta
fluido y no burocrático.

### Pendiente de decidir/construir para el Comprador (no existe todavía)

-   **Login con Google** al final del wizard (ver sección 6, es una
    decisión de producto con una recomendación de secuencia específica).
-   **Verificación real del celular** --- hoy en el wizard el comprador
    escribe su teléfono a mano, sin OTP. El sistema OTP ya existe (se
    usa para agentes) y se puede reutilizar para el comprador, pero no
    está conectado a este flujo todavía.
-   Autocompletar nombre/foto vía Google Sign-In.
-   Registrar como evento anónimo y agregado los filtros que usa el
    comprador en la barra de búsqueda (zona, presupuesto, tipo de
    propiedad, ambientes) --- esto no es una función del comprador en
    sí, pero es un dato que se genera en su recorrido y hoy no se está
    guardando (ver sección 8, es la base del dashboard de "oportunidades
    de mercado" para el agente).

## 2.2 Agente / Agencia

Un agente pertenece a una `Agency` (inmobiliaria). El login es **por
teléfono + código OTP** (sin contraseña) --- esto ya está construido y
probado.

Flujo real hoy:

1.  El agente ingresa su celular en `/agencia`.
2.  Recibe un código (en modo desarrollo se muestra en pantalla; en
    producción habría que conectar un proveedor real de SMS).
3.  Al verificar el código, entra a un dashboard propio (ruta
    `/agencia`, componente `AgentDashboard`) con:
    -   Métricas: ofertas nuevas, oportunidades activas, contactos
        revelados, cantidad de publicaciones.
    -   Pestaña **Ofertas**: lista de ofertas recibidas sobre sus
        propiedades, con acciones estructuradas (aceptar / contraofertar
        con rango fijo / declinar / revelar contacto) --- nunca campo de
        texto libre, por la misma razón que del lado comprador: si se
        permitiera texto libre, el agente podría escribir su propio
        teléfono en la respuesta y saltear el pago.
    -   Pestaña **Oportunidades**: actividad reciente sobre sus
        propiedades (vistas, guardados, comparaciones, consultas,
        visitas pedidas).
    -   Pestaña **Mi cuenta**: editar nombre de la agencia, vincular
        publicaciones nuevas por teléfono (`relink-by-phone`).
4.  Para ver el contacto real de un comprador que ofertó, el agente
    tiene que "revelar" --- eso dispara un gate de pago (hoy mockeado,
    sin pasarela real conectada).

### Pendiente de decidir/construir para el Agente (no existe todavía)

-   **Múltiples teléfonos por agencia.** Hoy `Agency.phone` es un solo
    campo. Si un agente tiene celular personal + línea de oficina, ambos
    deberían disparar la vinculación automática de publicaciones. Hace
    falta una tabla `AgencyPhone` (agencia, teléfono, verificado_en).
-   **Instagram obligatorio + link opcional, con revisión manual.** No
    existen esos campos ni una cola de revisión. Hoy `verified` es un
    booleano que nadie setea desde una pantalla real --- hace falta un
    panel interno (aunque sea mínimo, protegido por clave fija) donde
    una persona del equipo de Propomi vea el Instagram/link de cada
    agencia y apruebe o rechace.
-   **Dos estados separados de habilitación:** hoy, apenas se verifica
    el OTP, el agente ya tiene dashboard completo. Con la regla de
    revisión manual, hacen falta dos estados: "cuenta creada" (dashboard
    básico, puede ver que tiene leads esperando, para generarle
    intención de pagar/verificarse) vs. "perfil verificado" (puede
    revelar contacto / pagar). Ver sección 6 para la decisión pendiente
    sobre qué exactamente puede ver un agente no verificado.
-   **Dashboard de oportunidades de mercado por demanda agregada**
    (zona + rango de precio + ambientes, cruzado contra lo que la
    agencia tiene publicado en esa zona). Depende de que exista el
    evento de búsquedas (sección 8).
-   **Carga de propiedades por link de portal o alta manual**, para
    agentes ya verificados (hoy todas las propiedades son datos fijos de
    demo).
-   **Portal propio en subdominio** (`suagencia.propomi.com` o similar)
    --- infraestructura nueva, no un ajuste chico. Requiere subdominios
    wildcard (por ejemplo Namecheap con nameservers en Cloudflare) +
    middleware de Next.js que detecte el subdominio y filtre las
    propiedades por agencia. El mismo funnel de precio (oferta → reveal
    pago) tiene que correr igual dentro del subdominio, no una versión
    reducida.
-   **Links compartibles por propiedad con tracking de origen** (para
    que el agente pueda pautar en redes y medir de qué canal vienen los
    leads que llegan a ofertar). No existe tracking de origen todavía.

# 3. Estado real del código HOY

**Actualizado 2026-09-15.** Esta sección refleja el código en `main`, no el plan histórico.

## 3.1 Arquitectura

-   **Backend:** Python, FastAPI, SQLAlchemy 2.0, `DATABASE_URL` (SQLite
    en dev / Postgres en Render). Un único archivo
    `apps/api/app/main.py` concentra modelos, endpoints y migración
    incremental de columnas (`ensure_schema_columns`). Crawler en
    `apps/api/app/crawler/` (runner de 2 etapas, 7 parsers, dedup,
    normalize, links, selectors, cursores de paginación).
-   **Frontend:** Next.js (App Router), React, TypeScript, CSS propio en
    `globals.css`. Middleware de subdominios (`middleware.ts`) +
    `/tienda/[slug]`.
-   **Auth:** JWT. Guest comprador, OTP de agente, Google opcional para
    comprador (SMS verificado alcanza desde commit `7de1dff`).
-   **Deploy:** frontend Vercel, backend Render (`render.yaml`). Crons de
    antigüedad y crawler documentados en `render.yaml` (comentados si el
    plan no soporta cron; alternativa: scheduler externo con
    `X-Admin-Key`).
-   **Inventario:** ~56 endpoints, 18 tablas (incluye `CrawlCursor`),
    **40 tests** pasando en `apps/api/tests/`.

## 3.2 Backend --- lo que YA funciona

-   Modelos principales: `Agency`, `AgencyPhone`, `Property` (con
    `images`, `origin_published_at`, `hidden_at`, dedup/listing_group),
    `Offer`, `Lead`, `Event`, `Subscription`, `LeadCredit`,
    `ColdStartTask`, `CrawlCursor`, `RevealTransaction`, OTP, etc.
-   Auth: guest, OTP (Vonage real configurable), Google opcional.
-   Catálogo: `GET /properties` (filtros + oculta `hidden_at` y frescura
    por `last_seen_at`), `GET /properties/{id}`, filtros, review-queue,
    grupos de listing, alta manual e ingest para agentes verificados.
-   Ofertas / leads / reveal con cupo (free → plan → pay-per-lead) y
    bloqueo si `verification_status != VERIFIED`.
-   Lemon Squeezy: checkout hosteado + webhook HMAC.
-   Admin: cola de agencias, cold-start, crawler run, expire-stale.
-   Analytics: `search_performed`, `/analytics/demand`, oportunidades.
-   Crawler: CordobaProp `enabled=True`. ZonaProp preparado (queries/
    links/parser + fixture) pero **`enabled=False`** por Cloudflare
    challenge (403) al 2026-09-15. Argenprop/ML/Properati bloqueados en
    el borde.

## 3.3 Frontend --- lo que YA funciona

-   Landing + catálogo, `IntentWizard`, dashboard de agencia (ofertas,
    leads, demanda, cuenta), panel admin, onboarding por token, tienda
    por slug/subdominio.
-   Google opcional; SMS alcanza para enviar oferta.

## 3.4 Lo que sigue incompleto / bloqueado

-   ZonaProp (y el resto de portales con bot protection) sin anti-bot.
-   Crons de Render dependen del plan; documentados comentados.
-   Envío cold-start sigue siendo manual (cola admin lista).
-   Datos seed de demo siguen presentes para desarrollo local.

# 4. Modelo de datos

## 4.1 Modelo actual (implementado)

-   `Agency`: id, name, slug, city, phone, verified (legacy), claimed,
    `verification_status` (PENDING|VERIFIED|REJECTED), priority, notes,
    instagram, website_link, campos de monetización legacy migrados a
    tablas propias.
-   `AgencyPhone`: múltiples teléfonos por agencia.
-   `Property`: campos de ficha + `images` (lista JSON, hasta 5),
    `origin_published_at` (texto del portal), `detected_at` /
    `last_seen_at`, `needs_review`, `possible_duplicate_of`,
    `listing_group_id`, **`hidden_at`** (nullable; ocultar por
    antigüedad sin borrar).
-   `Offer` / `Lead` + reveal con `contact_revealed`.
-   `Event` (incluye `search_performed` agregado/anónimo).
-   `Subscription` + `LeadCredit` por agencia.
-   `ColdStartTask` + onboarding token.
-   **`CrawlCursor`:** `source_id` (PK), `last_page`, `last_run_at`,
    `total_seen` — paginación con estado del crawler.
-   Migración: `ensure_schema_columns()` agrega columnas faltantes sin
    borrar datos. Filas existentes quedan con `hidden_at = NULL`
    (visibles) hasta el primer `expire-stale`.

## 4.2 Ya no pendiente (cerrado respecto del plan histórico)

Los ítems que la versión anterior de este documento listaba en 4.2
(`AgencyPhone`, `images`, `origin_published_at`, `verification_status`,
`Subscription`, `LeadCredit`, `search_performed`) **están implementados**.
Pendientes de producto/ops: habilitar más fuentes de crawl cuando dejen
de estar detrás de bot protection, y activar crons en el plan de Render
(o scheduler externo).

# 5. Reglas de negocio no negociables (privacidad / anti-fuga)

Estas reglas ya están construidas y probadas en el backend actual.
**Cualquier cambio futuro tiene que preservarlas** --- son las que
sostienen que el modelo de "pagás para revelar el contacto" no se rompa
con un simple copy-paste:

1.  **El comprador nunca escribe texto libre para condiciones.** Todo lo
    que podría filtrar su contacto (teléfono, email, links) está
    resuelto con chips/botones predefinidos, nunca un `<textarea>`
    abierto.
2.  **El agente nunca responde con texto libre.** Aceptar, contraofertar
    (dentro de un rango fijo) o declinar son las únicas acciones --- así
    no puede escribir su propio contacto en la respuesta para saltear el
    pago.
3.  `sanitize_free_text()` **rechaza teléfonos, emails, usuarios y
    links** en cualquier campo de comentario que sí exista. Este filtro
    tiene que aplicarse también a la **descripción scrapeada del portal
    de origen** cuando el crawler esté conectado --- hoy solo se aplica
    a lo que un comprador o agente escribe dentro de Propomi. Si no se
    limpia el texto que viene copiado tal cual del portal original
    (donde suele aparecer "Contactar al 11-xxxx-xxxx"), todo el negocio
    se rompe con un copy-paste de la inmobiliaria original.
4.  `buyer_name`**,** `buyer_phone`**,** `buyer_email` **nunca viajan en
    ninguna respuesta de API** salvo que `contact_revealed = true` para
    esa oferta puntual.
5.  **La identidad canónica de agente es el teléfono normalizado
    (E.164), no el email.**
6.  **El canal B2B (agente↔agente) es 100% gratis siempre**, para ambos
    lados --- es un mecanismo de crecimiento/adopción que reemplaza los
    grupos de WhatsApp entre colegas. **No puede usarse para reenviar un
    contacto de comprador ya capturado por el canal B2C** --- eso sería
    saltear el único canal pago.
7.  **El crawler nunca dispara contacto en frío al publicar una
    propiedad** --- solo cuando llega una oferta real (B2C) o una
    consulta B2B.

# 6. Decisiones de producto

Esta sección separa lo que **ya está decidido y confirmado** de lo que
son **defaults recomendados pendientes de confirmación** del dueño del
producto. Si quien construye esto es una IA sin supervisión humana
inmediata, debe **avanzar con el default recomendado** y dejarlo
señalado como reversible, no bloquearse esperando respuesta.

## 6.1 Ya decidido (no reabrir)

-   Solo venta, nunca alquiler.
-   Identidad canónica de agente = teléfono, no email.
-   Matrícula profesional: se pide pero no es obligatoria (existe opción
    "sin matrícula/particular/comisionista") para no cerrar la puerta al
    mercado informal.
-   Zona piloto: Caballito, CABA.
-   Filtros del crawler: máximo 90 días de antigüedad al indexar (ver
    6.2 sobre el filtro periódico), solo venta, hasta 5 fotos por
    propiedad.
-   Canal B2B siempre gratis para ambos lados.
-   Pricing base: pay-per-lead \~USD 5, suscripciones USD 30 (30 leads)
    / USD 50 (60 leads) / USD 99 (ilimitado). Umbral de USD 60/mes para
    acceder a la función "Búsquedas particulares" (demanda genérica
    premium).
-   Duplicados de la misma propiedad publicada por varios agentes: se
    fusionan en una ficha con precio en rango, se notifica a todos a la
    vez, gana el que revela primero, con cola de prioridad por
    antigüedad de suscripción (timeout 24h si hay suscriptores, 6h si no
    hay ninguno).

## 6.2 Defaults recomendados --- pendientes de confirmación explícita del dueño del producto

Para cada uno se indica la recomendación y el motivo. Si nadie los
contradice, **construir con este default**:

1.  **Login de Google (comprador) — REVERTIDO 2026-09-14 (commit
    `7de1dff`):** la decisión original pedía Google Sign-In obligatorio
    además del SMS en el último paso del wizard. Se revirtió: **el SMS
    verificado alcanza**; Google quedó opcional. *Motivo:* el doble gate
    mataba la conversión al final del wizard (exactamente la fricción
    que el diseño de 3 pantallas buscaba evitar). No reabrir sin datos
    nuevos de conversión.
2.  **Qué ve un agente NO verificado en su dashboard:** puede ver que
    **tiene leads esperando** (cantidad, no el detalle ni el contacto)
    --- para generarle la ansiedad de completar la verificación. No
    puede revelar contacto ni pagar hasta estar verificado. *Motivo:*
    alineado con la lógica de "cold start" del propio proyecto (se le
    avisa que hay una propuesta esperando, sin exponer nada, y eso
    empuja a que se verifique).
3.  **Qué cuenta como "lead" consumible contra el cupo de la
    suscripción:** un **reveal de contacto**, no cualquier oferta
    recibida. Los planes de USD 30/50/99 son packs de reveals. *Motivo:*
    es lo único que tiene costo real de oportunidad para Propomi
    (mostrar el contacto), y es coherente con "pagás para develar el
    contacto", el pitch central del producto.
4.  **Excedente de cupo dentro del mismo ciclo:** permitir seguir
    revelando a precio pay-per-lead individual (\~USD 5) en vez de
    bloquear hasta el próximo ciclo o forzar upgrade. *Motivo:* patrón
    estándar de SaaS; evita perder un lead caliente por falta de cupo,
    que sería perder exactamente el momento de mayor intención de
    compra.
5.  **Billing por agencia, no por agente individual.** Si una persona
    administra varias inmobiliarias, cada `Agency` paga su propio plan.
    *Motivo:* las propiedades y el futuro subdominio propio se organizan
    por agencia, no por persona.
6.  **Subdominio propio:** bundleado dentro de las suscripciones de USD
    50 y USD 99 (no en la de USD 30 ni en pay-per-lead suelto).
    *Motivo:* funciona como incentivo de upgrade sin fragmentar el
    sistema de cobro en dos mecanismos paralelos (uno recurrente y uno
    de pago único).
7.  **Cold start (agencia todavía no reclamada, solo scrapeada):**
    notificar por **WhatsApp/SMS al teléfono scrapeado**, de forma
    automática y server-to-server, en vez de por mail. *Motivo:* el
    teléfono es el único dato que con certeza se va a tener siempre (es
    la clave de identidad elegida para todo el sistema); el email
    scrapeado del portal de origen es opcional y poco confiable. Ese
    teléfono nunca debe quedar expuesto públicamente ni usarse como
    identificador visible en ningún lado, solo para esta notificación
    puntual server-to-server.
8.  **Prevención de abuso de los 10 leads gratis:** la revisión manual
    de Instagram/link antes de habilitar el cupo gratis es el freno
    principal. Además, dejar como regla explícita para quien revise a
    mano: sospechar de perfiles nuevos con el mismo nombre de agencia,
    misma zona de propiedades, o mismo patrón de Instagram recién creado
    que otro perfil ya rechazado.
9.  **Política de reembolso/disputa:** si un agente paga por revelar un
    contacto y el teléfono está mal o el comprador nunca responde, dar
    **crédito a favor** (no reembolso en efectivo) para un próximo
    reveal, con un límite razonable de disputas por mes para evitar
    abuso. *Motivo:* sostiene la confianza en el modelo de pago sin
    abrir una vía de reembolsos en cascada; hay que definirlo y
    comunicarlo ANTES del lanzamiample, no después del primer reclamo
    real.

# 7. El crawler --- estado real (2026-09-15)

El crawler **existe** en `apps/api/app/crawler/`:

-   Runner de 2 etapas (listado → detalle), parsers por fuente basados
    en JSON embebido / JSON-LD (no solo CSS frágil).
-   Dedup por fingerprint zona|dirección|precio|superficie|ambientes;
    candidatos a revisión manual / `listing_group_id`.
-   Limpieza de contacto en descripción scrapeada (`strip_contact_leaks`).
-   **`MAX_AGE_DAYS = 90`**: filtro de entrada + proceso periódico
    `expire_stale_properties` / `POST /admin/properties/expire-stale`
    que setea `hidden_at` (no borra). Upsert resetea `hidden_at` si el
    aviso reaparece.
-   **Paginación con estado:** tabla `CrawlCursor`; al llegar al tope de
    la fuente reinicia a página 1. `MAX_DETAILS_PER_SOURCE = 40`,
    `REQUEST_DELAY_SECONDS = 1.0`.
-   Fuentes:
    -   `cordobaprop`: **enabled=True**
    -   `zonaprop`: código listo (Caballito/venta, robots respetado,
        fixture + test de parser) pero **enabled=False** — Cloudflare
        challenge en listados/fichas al 2026-09-15
    -   `argenprop` / `mercadolibre` / `properati`: 403 en el borde
    -   `mendozaprop` / `mercado_unico`: robots OK, falta validar HTML
        real antes de habilitar

Disparo: `POST /admin/crawler/run` (admin key). Cron diario documentado
en `render.yaml` (comentado si el plan no soporta cron jobs).

# 8. Sistema de monetización --- estado real

Implementado:

-   Tablas `Subscription` y `LeadCredit` por agencia.
-   Planes: `PLAN_30` (30 reveals), `PLAN_50` (60), `PLAN_99`
    (ilimitado), pay-per-lead ~USD 5.
-   Orden de consumo en reveal: free_leads → cupo de plan → pay-per-lead.
-   Excedente de cupo → pay-per-lead (no bloqueo duro).
-   Lemon Squeezy: checkout hosteado + webhook con verificación HMAC;
    mapeo variant→plan por env vars.
-   Reveal bloqueado si `verification_status != VERIFIED`.

Pendiente operativo: cargar secrets de Lemon Squeezy en Render cuando la
cuenta esté aprobada (`docs/LEMON_SQUEEZY_CHECKLIST.md`). Política de
disputa/reembolso sigue siendo decisión de producto documentada en 6.2.9.

# 9. Cold start --- cómo arrancar con catálogo scrapeado y cero agencias registradas

El problema concreto: en el arranque, una propiedad fue **scrapeada**,
no reclamada por su agencia. Lo único que se tiene de esa agencia es un
**teléfono** extraído del portal de origen --- que además está pensado
para **nunca** mostrarse ni usarse como identificador público. No hay
email todavía.

**Decisión recomendada (ver 6.2.7):** notificar automáticamente por
WhatsApp/SMS al teléfono scrapeado cuando llegue una oferta real sobre
esa propiedad, de forma server-to-server, sin exponer el número a nadie
más. El mensaje debe incluir el resumen de la propuesta (monto, sin el
contacto del comprador) y un link de onboarding para que la agencia
reclame (`claim`) su perfil y complete la verificación (Instagram/link).

Esto requiere en el futuro conectar la WhatsApp Cloud API (mencionado en
el roadmap original como algo a automatizar "cuando haya tracción" ---
al principio puede ser 100% manual, alguien del equipo mandando el
mensaje a mano).

# 10. Roadmap completo --- estado al 2026-09-15

| Etapa | Tema | Estado |
|---|---|---|
| 1 | Modelo de datos ampliado | **Hecho** |
| 2 | Identidad comprador (SMS + Google opcional) | **Hecho** (Google ya no obligatorio) |
| 3 | `search_performed` + demanda | **Hecho** |
| 4 | Panel revisión manual agencias | **Hecho** (backend + `/admin`) |
| 5 | Monetización Lemon Squeezy | **Hecho** (falta ops de secrets) |
| 6 | Cold start (cola + onboarding token) | **Hecho** (envío aún manual) |
| 7 | Ingesta / alta manual verificados | **Hecho** |
| 8 | Crawler real | **Hecho** (CordobaProp live; ZonaProp bloqueado por CF; antigüedad + cursores agregados 2026-09-15) |
| 9 | Subdominios por agencia | **Hecho** |

Próximas decisiones de producto (no técnicas):

1.  Qué hacer con el piloto Caballito si ZonaProp sigue detrás de
    Cloudflare (mover a Córdoba vs. anti-bot vs. otra fuente).
2.  Activar crons en Render o scheduler externo con `ADMIN_KEY`.
3.  Automatizar cold-start WhatsApp cuando haya tracción.

# 11. Checklist de calidad antes de entregar cualquier etapa

Antes de dar por terminada una etapa y empaquetarla para subir al repo
real, verificar:

-   [ ] El frontend compila (`npm run build`) sin errores ni warnings de
    imports faltantes.
-   [ ] Los tests del backend pasan (`pytest`) --- hoy hay 8 tests en
    `apps/api/tests/test_security.py`, cualquier cambio nuevo debe sumar
    sus propios tests, no romper los existentes.
-   [ ] Ninguna de las reglas no negociables de la sección 5 quedó rota
    (repasar cada una explícitamente).
-   [ ] `buyer_name`/`buyer_phone`/`buyer_email` siguen sin viajar en
    ninguna respuesta salvo `contact_revealed=true`.
-   [ ] No se agregó ningún campo de texto libre nuevo sin pasar por
    `sanitize_free_text()`.
-   [ ] Se entrega el **paquete completo** (todo `apps/web` y todo
    `apps/api` relevante), nunca archivos sueltos --- un import roto por
    un archivo faltante es el error más común y más evitable.
-   [ ] Se listan explícitamente las variables de entorno nuevas
    necesarias (y dónde cargarlas: Vercel para frontend, Render o
    equivalente para backend).
-   [ ] Si el modelo de datos cambió, se explica qué pasa con los datos
    que ya existen (migración vs. arranque de cero) --- nunca dejarlo
    implícito.

# 12. Problemas conocidos en el repo actual (a corregir, no a repetir)

-   **Estructura duplicada:** en una entrega reciente el repo terminó
    con `apps/apps/web` y `apps/apps/api` además de `apps/web` y
    `apps/api` --- carpetas idénticas duplicadas por un error de
    copiado. Hay que borrar la carpeta `apps/apps` completa (se confirmó
    que su contenido es idéntico a `apps/web`/`apps/api`, no tiene nada
    que no esté ya en el lugar correcto).
-   `freshness` **mezcla dos fechas distintas** (detección propia
    vs. antigüedad declarada por el portal de origen) --- ver sección
    4.2, hay que separarlo en dos campos antes de conectar el crawler
    real, si no las reglas de antigüedad no se pueden aplicar
    correctamente.
-   **Selectores del scraper sin verificar** contra HTML real de
    ZonaProp/Argenprop (repo `proferta-crawler`) --- no correr en
    producción sin antes validar con `test_parsers_con_html_local()`.
-   `PaymentGateway` **deniega todo por defecto** (correcto como
    comportamiento seguro por ahora) --- pero significa que hoy **nadie
    puede revelar contacto en producción** hasta que se conecte una
    pasarela real o se cambie el mock deliberadamente para pruebas
    controladas.

*Fin del documento. Cualquier ambigüedad que quede después de leer esto
en una etapa puntual del roadmap (sección 10) debe resolverse
consultando al dueño del producto antes de construir --- no asumir en
silencio, especialmente en todo lo que toca a privacidad del contacto
del comprador (sección 5) y a dinero (secciones 6 y 8).*
