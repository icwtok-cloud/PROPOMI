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
7.  El elefante en la habitación: el crawler (no existe todavía)
8.  Sistema de monetización --- lo que falta construir
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

**Importante:** esta sección describe lo que existe de verdad en el
repo, no lo planeado. Todo lo marcado como "no existe" en las secciones
anteriores tampoco está acá --- no se repite.

## 3.1 Arquitectura

-   **Backend:** Python, FastAPI, SQLAlchemy 2.0, base de datos vía
    `DATABASE_URL` (SQLite en desarrollo). Un único archivo
    `apps/api/app/main.py` concentra modelos, endpoints y lógica de
    migración incremental de columnas (agrega columnas nuevas a tablas
    existentes sin borrar datos, comprobando si ya existen antes de
    correr el `ALTER TABLE`).
-   **Frontend:** Next.js (App Router), React, TypeScript, sin librería
    de componentes --- CSS propio en `apps/web/app/globals.css`.
-   **Autenticación:** JWT propio. Dos flujos: sesión de comprador tipo
    "guest" (`POST /auth/guest`, sin dato personal) y login de agente
    por OTP (`POST /auth/otp/request` + `POST /auth/otp/verify`).
-   **Repos:**
    -   `github.com/icwtok-cloud/PROPOMI` --- el monorepo (frontend +
        backend), el más avanzado.
    -   `github.com/icwtok-cloud/proferta-crawler` --- pipeline de
        crawler, separado, con selectores de scraping **sin verificar
        contra HTML real todavía** (etapas 1-2, scraping de
        ZonaProp/Argenprop) y etapas de normalización/dedup/anti-fuga
        (etapas 3-8) que no están conectadas al backend de PROPOMI
        todavía.
-   **Deploy:** frontend en Vercel (`propomi.vercel.app`), hay un
    `render.yaml` para el backend (Render).

## 3.2 Backend --- lo que YA funciona y está probado (`apps/api/app/main.py`)

-   Modelos: `Agency`, `Property`, `Offer`, `Event` (para tracking de
    interacciones tipo vista/guardado/comparación/etc.).
-   `POST /auth/guest` --- sesión anónima de comprador.
-   `POST /auth/otp/request` / `POST /auth/otp/verify` --- login de
    agente por teléfono. En modo desarrollo devuelve el código en la
    respuesta (`dev_code`) para poder probar sin SMS real.
-   `GET /properties` (con filtros: zona, tipo, operación, ambientes,
    precio máximo, cochera, apto crédito, agencia) y
    `GET /properties/{id}`.
-   `POST /events` y `GET /events/funnel` --- tracking de interacciones
    del comprador.
-   `POST /intents` --- guarda la intención/contexto detrás de una
    interacción (por ejemplo los datos completos del wizard de oferta).
-   `POST /offers` --- crea una oferta. Valida:
    -   `buyer_name`, `buyer_phone` obligatorios.
    -   `buyer_email` opcional, con formato validado por regex simple
        (sin dependencia externa de validación de email).
    -   El campo `comment` pasa por `sanitize_free_text()`, un filtro
        anti-fuga que **rechaza teléfonos, emails, usuarios y links**
        --- esto es lo que impide que alguien escriba su contacto real
        dentro de la oferta para saltear el pago. Hoy este filtro corre
        sobre el `comment`, que en el frontend actual se arma
        automáticamente a partir de los chips de condiciones
        seleccionados (el comprador ya no escribe texto libre ahí).
-   `GET /offers` --- lista ofertas (para agente, filtradas por sus
    propiedades; para comprador, las propias). Nunca devuelve
    `buyer_name`/`buyer_phone`/`buyer_email` salvo que
    `contact_revealed = true`.
-   `POST /offers/{id}/counter` --- contraoferta.
-   `POST /offers/{id}/reveal` --- el corazón del negocio. Verifica cupo
    de suscripción o dispara el gate de pago (`PaymentGateway`, hoy un
    mock que **deniega por defecto**); solo si hay cupo o pago
    confirmado, devuelve `buyer_name`/`buyer_phone`/`buyer_email`.
-   `POST /payments/{transaction_id}/mock-complete` --- endpoint de
    desarrollo para simular un pago exitoso sin pasarela real conectada.
-   `AgentSuppressionList` + `POST /contact-requests` +
    `POST /agencies/{id}/opt-out` --- lista de supresión para que una
    agencia pueda optar por no recibir más solicitudes de contacto de
    cierto tipo.
-   `GET /agencies/{id}/opportunities` --- actividad agregada (vistas,
    guardados, etc.) sobre las propiedades de una agencia.
-   `GET /agencies/{id}` / `PATCH /agencies/{id}` --- perfil de agencia.
-   `POST /agencies/{id}/relink-by-phone` --- vuelve a vincular
    publicaciones nuevas detectadas con el mismo teléfono de la agencia.
-   `GET /analytics/summary` --- conteo simple de
    propiedades/eventos/ofertas y funnel por tipo de evento.
-   Identidad canónica de agente: **teléfono normalizado en formato
    E.164** (usando la librería `phonenumbers`), no email.
-   Tests: `apps/api/tests/test_security.py`, 8 tests, **todos pasando**
    --- cubren el flujo de seguridad central (reveal invertido
    corregido, gate de pago, filtro anti-fuga, lista de supresión).

## 3.3 Frontend --- lo que YA funciona (`apps/web`)

-   `app/page.tsx` --- landing + catálogo de propiedades con filtros
    (incluye **tipo de propiedad** como campo de búsqueda, agregado
    recientemente junto a ubicación/presupuesto/ambientes).
-   `app/agencia/page.tsx` --- ruta dedicada que renderiza
    `AgentDashboard` (ya no es una pestaña dentro de la landing, es una
    URL propia).
-   `components/OfferModal.tsx` --- el wizard de 3 pantallas descrito en
    2.1.
-   `components/AgentDashboard.tsx` --- login por OTP + dashboard con
    las 3 pestañas descritas en 2.2. Tiene su propia sesión persistida
    en `localStorage` (`propomi-agent-session`), separada de la sesión
    de comprador (`propomi-buyer-session`).
-   `components/AgentOfferActions.tsx` --- botones estructurados de
    aceptar/contraofertar/declinar/revelar dentro de cada oferta, sin
    texto libre.
-   `components/ComparePanel.tsx`, `components/PropertyCard.tsx`,
    `components/BuyerIdentityModal.tsx` --- soporte de catálogo y
    captura de identidad del comprador.
-   `lib/api.ts` --- cliente HTTP tipado hacia el backend, con modo demo
    (si no hay `DATABASE_URL`/backend configurado, usa datos locales
    fijos para poder probar el frontend solo).
-   `lib/types.ts` --- tipos compartidos (ver sección 4.1 para el
    detalle completo).
-   Isotipo con dos colores (la palabra "omi" dentro de "propomi" en un
    color distinto al resto) y barra de búsqueda responsive corregida
    (el bug de un botón circular que se rompía en mobile ya está
    solucionado).
-   Sin ninguna opción de alquiler en ningún lado de la interfaz --- el
    tipo `Property.operation` es literalmente `'Venta'`, no hay forma de
    seleccionar otra cosa.

## 3.4 Lo que es demo/mock (no confundir con "producción funcionando")

-   Todas las propiedades hoy son **datos fijos** (`lib/data.ts` en el
    frontend, `DEMO` en el backend) --- no hay crawler real corriendo.
-   El pago (`PaymentGateway`) es un mock que deniega por defecto; no
    hay integración real con Mercado Pago/Stripe.
-   El envío de OTP por SMS no está conectado a un proveedor real --- en
    desarrollo el código se devuelve en la respuesta de la API.
-   No hay panel de revisión manual de agencias.
-   No hay sistema de suscripciones/planes con cupo de leads --- el gate
    de pago existe a nivel de "revelar este contacto puntual", pero no
    hay tablas de plan/ciclo/cupo consumido.

# 4. Modelo de datos

## 4.1 Lo que existe hoy (tal cual está tipado en `lib/types.ts` / modelado en `main.py`)

-   `Agency`: id, name, city, verified (booleano simple), claimed
    (booleano), phone (un solo campo).
-   `Property`: id, title, type, operation ('Venta' fijo), price,
    currency, zone, city, country, surface, rooms, bedrooms, bathrooms,
    parking, pool, balcony, petFriendly, credit, freshness (texto único,
    mezcla antigüedad real y fecha de detección --- ver problema en
    sección 12), source, sourceUrl, **image** (string único, no lista),
    description, agencyId, detectedAt, lastSeenAt.
-   `Offer`: id, user_id, property_id, amount, currency, payment_form,
    capital, timeframe, comment, status, created_at, contact_revealed,
    buyer_name, buyer_phone, buyer_email (todos estos tres últimos solo
    visibles si contact_revealed=true).
-   `Event`: registro de interacción (vista, guardado, comparación,
    consulta, pedido de visita, oferta creada, contacto
    solicitado/compartido, contraoferta, negociación iniciada, avance de
    operación).
-   `Intent`: contexto libre asociado a un evento (budget, capital,
    financing, timeframe, decisionMaker, alternatives, comment).
-   `Opportunity`: proyección de `Event` para el dashboard de agencia.
-   `BuyerProfile`: name, phone, email (opcional) --- la identidad que
    el comprador deja en la pantalla 3 del wizard.
-   `Session`: token + user (id, phone, role, agency_id).

## 4.2 Lo que hay que agregar (según lo definido en el brief de negocio y en la auditoría de reglas)

-   `AgencyPhone`: tabla nueva --- agencia, teléfono, verificado_en. Un
    agente puede tener celular personal + línea de oficina; ambos deben
    disparar la nucleación automática de publicaciones
    (`relink-by-phone` tiene que buscar contra todos los teléfonos de la
    agencia, no solo uno).
-   `Property.images`: cambiar de `image` (string) a **lista de hasta 5
    URLs**. Esto rompe compatibilidad con los datos de demo actuales ---
    hace falta decidir explícitamente si se migra el dato viejo (`image`
    → `images: [image]`) o se arranca de cero (ver sección 6, decisión
    pendiente).
-   **Separar** `freshness` **en dos campos reales:** `detected_at`
    (cuándo el crawler de Propomi la vio por primera vez) y
    `origin_published_at` (lo que el portal de origen declara, por
    ejemplo "publicado hace 3 días" --- hay que preservarlo tal cual
    viene, no reemplazarlo).
-   **Verificación en dos niveles para agencia:** hoy `verified` es un
    booleano. Hace falta algo como `verification_status` con al menos
    dos estados (`PENDING`, `VERIFIED`, y probablemente `REJECTED`), más
    los campos `instagram` (obligatorio) y `website_link` (opcional) que
    se revisan a mano. Además una prioridad de cola
    (`verification_priority`) que ponga primero a quien ya se suscribió
    antes de verificarse, con SLA de 24 horas.
-   `Subscription`: por agencia --- plan activo, cupo de leads del
    ciclo, leads consumidos, fecha de renovación.
-   `LeadCredit`: contador de leads gratis al verificarse (los
    primeros 10) --- tiene que descontarse contra el mismo contador que
    usa la suscripción para que no se dupliquen ni se pisen entre sí.
-   **Evento** `search_performed`: hoy no se registra ninguna
    búsqueda/filtro que use el comprador en la barra (zona, presupuesto,
    tipo, ambientes). Sin este evento no hay materia prima para el
    dashboard de "oportunidades de mercado" del lado agencia. Tiene que
    guardarse de forma **agregada y anónima** --- nunca asociado a un
    comprador identificable.

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

1.  **Orden del login de Google (comprador):** wizard completo primero,
    sin pedir login para navegar/comparar/ofertar. Recién **en el último
    paso**, antes de poder apretar "Enviar oferta", pedir Google Sign-In
    (además del teléfono verificado por OTP, que Google no valida).
    *Motivo:* pedir login al entrar reintroduce la fricción que el
    wizard de 3 pantallas está diseñado para evitar; pedirlo cuando la
    persona ya invirtió tiempo completando los pasos convierte mucho
    mejor (aversión a la pérdida / compromiso y consistencia).
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

# 7. El crawler --- no existe todavía, no prometer fechas sin construirlo

Hoy **no hay ningún crawler corriendo.** Las propiedades que se ven en
el producto son datos fijos de demostración. Antes de prometer fechas de
lanzamiento con catálogo real, esto tiene que construirse desde cero.
Reglas que va a tener que cumplir:

-   **Hasta 5 fotos por propiedad** → requiere que `Property.images` sea
    lista (ver sección 4.2).
-   **Filtro de antigüedad de 90 días (o 60, según la etapa ---
    confirmar cuál rige) no alcanza solo al indexar.** Una propiedad
    indexada hace 55 días va a superar el límite mientras sigue
    publicada en Propomi sin que nadie la vuelva a mirar --- hace falta
    un **proceso periódico (cron diario)** que la oculte al cumplir el
    límite, no solo un filtro de entrada.
-   **Preservar la antigüedad declarada por el portal de origen**
    ("publicado hace 3 días") como un dato separado de la fecha en que
    el crawler de Propomi la detectó --- hoy el campo `freshness` mezcla
    ambas cosas sin distinguir (ver 4.2).
-   **Limpiar contacto también en el texto scrapeado**, no solo en lo
    que un usuario escribe dentro de Propomi (ver regla no negociable #3
    de la sección 5).
-   **Deduplicación entre portales.** Es habitual que dos agentes
    publiquen la misma propiedad física en distintos portales, o que el
    mismo agente la suba dos veces. Sin una regla de "esto es la misma
    propiedad", se le puede llegar a cobrar a dos agencias distintas por
    el mismo lead sobre el mismo departamento --- un riesgo de confianza
    serio. No hace falta IA sofisticada para la primera versión: alcanza
    con una regla simple --- mismo rango de precio + misma zona +
    superficie casi igual = candidato a duplicado, marcado para
    **revisión manual** (no fusión automática todavía).
-   **Selectores CSS sin verificar contra HTML real.** El repo
    `proferta-crawler` tiene un `proferta_scraper.py` con selectores
    para ZonaProp/Argenprop que todavía no se probaron contra el HTML
    real de esos sitios --- hay una función
    `test_parsers_con_html_local()` pensada para eso, pero no se corrió
    en serio todavía.

# 8. Sistema de monetización --- falta el modelo de datos completo

Los montos (\~USD 5 pay-per-lead; USD 30/50/99 de suscripción) son un
dato, no un sistema. Falta construir:

-   La tabla `Subscription` por agencia (plan activo, cupo del ciclo,
    consumido, renovación) --- ver 4.2.
-   El contador `LeadCredit` de los primeros 10 leads gratis al
    verificarse, descontado contra el mismo contador que la suscripción
    (ver 4.2 y decisión 6.2.3).
-   Prevención de abuso de cuentas duplicadas para repetir el cupo
    gratis (ver decisión 6.2.8).
-   Política de disputa/reembolso explícita (ver decisión 6.2.9),
    documentada y visible **antes** del lanzamiento.
-   Conectar una pasarela de pago real (Mercado Pago y/o Stripe) --- el
    "seam" (punto de integración) ya existe en el backend vía
    `PaymentGateway`, pero hoy es un mock que deniega por defecto.
-   **El dashboard de oportunidades de mercado** (demanda agregada por
    zona/precio/ambientes cruzada contra el catálogo propio de la
    agencia) depende de que exista el evento `search_performed` (sección
    4.2) generando volumen real primero.

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

# 10. Roadmap completo, en orden de dependencia

Cada etapa depende de que la anterior esté terminada y probada. No es un
orden arbitrario --- está pensado así porque etapas posteriores
necesitan datos/infraestructura que generan las anteriores.

1.  **Modelo de datos ampliado:** `AgencyPhone` (múltiples teléfonos),
    Instagram/link + verificación en dos niveles, `Property.images` como
    lista (con decisión explícita sobre migración de datos viejos),
    `Subscription` y `LeadCredit`.
2.  **Login de Google para compradores** + reutilización del OTP
    existente para verificar el celular, en el orden definido en 6.2.1.
3.  **Evento** `search_performed`**:** loguear búsquedas/filtros del
    comprador de forma agregada y anónima --- base para el dashboard de
    oportunidades de mercado.
4.  **Panel de revisión manual de agencias** (mínimo viable: una
    pantalla interna, protegida por clave fija, donde se vean perfiles
    pendientes con su Instagram/link y se aprueben o rechacen --- cola
    ordenada por prioridad de suscripción, SLA 24hs).
5.  **Sistema de monetización completo:** planes, contador de leads,
    reveal pago conectado a pasarela real, los 10 leads gratis al
    verificarse, política de reembolso documentada y visible.
6.  **Cold start real:** notificación automática al teléfono scrapeado
    con el resumen de la propuesta + link de onboarding (empezar 100%
    manual, dejar el lugar para automatizar con WhatsApp Cloud API
    después).
7.  **Ingesta de propiedades por URL o alta manual**, habilitado para
    agentes ya verificados.
8.  **Crawler real**, con las reglas de antigüedad (filtro de entrada +
    proceso periódico), 5 fotos, deduplicación simple por
    zona/precio/superficie, y limpieza de contacto en el texto scrapeado
    (no solo en lo que escribe un usuario dentro de Propomi).
9.  **Subdominios por agencia** (`suagencia.propomi.com`) con el mismo
    funnel de precio corriendo adentro, y **links compartibles con
    tracking de origen** por propiedad --- dejar para el final porque es
    infraestructura nueva y no bloquea nada de lo anterior. Ambas cosas
    dependen de que existan agencias verificadas y con catálogo propio
    real (etapas 1, 4 y 7).

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
