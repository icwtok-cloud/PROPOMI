# Anti-bot / ampliación de fuentes — research (sin implementación)

Fecha: 2026-09-15  
Contexto: 6 fuentes live (cordobaprop, inmoup, mendozaprop, mercado_unico,
mercadolibre, inmoclick). ZonaProp / Argenprop / Properati (y similares)
caen por challenge de borde (Cloudflare / CloudFront / ELB), no por falta
de JSON-LD o HTML parseable.

**Decisión de producto:** este documento no elige implementación. Solo
compara rutas con costos y trade-offs realistas.

---

## Ruta 1 — Proxy residencial / API de scraping

**Servicios de referencia:** Bright Data, Oxylabs, ScraperAPI, Smartproxy.

| Aspecto | Estimación |
|---|---|
| Costo mensual | **USD 50–300+** según plan. Orientativo: ScraperAPI ~USD 49/100k req; residencial Bright Data suele cotizarse por GB (**USD 8–15/GB**). Con 6 portales bloqueados × 80 details × 4 corridas/mes ≈ pocos miles de req; el costo real sube si hay reintentos por challenge. |
| Tiempo de integración | **3–7 días**: cliente HTTP con proxy URL, rotación, retries, métricas de 403/challenge. |
| Legalidad / ToS | **Alto riesgo ToS**: la mayoría de portales prohíben scraping automatizado. Proxy residencial no cambia la relación contractual con el portal; solo reduce detección técnica. Revisar ToS de ZonaProp/Argenprop antes de producción. |
| Volumen desbloqueable | Potencialmente **los 3 grandes** (ZonaProp, Argenprop, Properati) + listados ML si vuelven a endurecerse: orden de **cientos de miles** de avisos nacionales (ZP declara ~700k en rankings públicos; no todo es piloto 4 provincias). |
| Riesgo técnico | Medio: Cloudflare Turnstile / JS challenge puede seguir fallando con solo proxy HTTP. A menudo se combina con ruta 2. |

**Pros:** sin cambiar arquitectura del crawler (sigue `requests`/curl-like).  
**Contras:** costo variable; ToS; dependencia de terceros.

---

## Ruta 2 — Headless (Playwright) + stealth en worker aparte

| Aspecto | Estimación |
|---|---|
| Costo infra | **USD 14–50/mes** un service extra en Render (o Fly/Railway) con más RAM (Playwright ~1 GB). Más si hay browser pool. |
| Tiempo de integración | **1–3 semanas**: worker separado, cola de jobs, selectores/espera de challenge, extracción post-render, observabilidad. |
| Legalidad / ToS | Mismo problema de ToS que la ruta 1. |
| Volumen desbloqueable | Similar a ruta 1 **si** el stealth supera el challenge de forma estable. |
| Riesgo técnico | **Alto frente a Cloudflare Turnstile** y fingerprinting moderno: stealth plugins se rompen con frecuencia; mantenimiento continuo. |

**Pros:** ve el DOM real post-JS (útil también para SPAs tipo Propia/Mudafy).  
**Contras:** frágil; CPU/tiempo por ficha (segundos, no ms); ops más pesada que el crawler actual.

---

## Ruta 3 — Acuerdos comerciales (colegios / Tokko / feeds)

| Actor | Qué se sabe (research público) |
|---|---|
| **Colegios provinciales** (CPI Córdoba → CórdobaProp; CCPIM Mendoza → MendozaProp; COCIR Rosario → Propia) | Ya tenemos HTML/sitemap en algunos. Un **acuerdo formal** podría habilitar feed CSV/API o mayor frecuencia sin pelear anti-bot. Proceso: contacto comercial/institucional, NDA, posible canje de leads o fee mensual — **plazos 1–3 meses**, no días. |
| **Tokko Broker** (CMS multi-tenant usado por muchas inmobiliarias AR) | Producto orientado a inmobiliarias; integraciones/API suelen ser **B2B hacia la inmobiliaria**, no un dump nacional abierto. Cotización caso a caso; no hay tarifa pública de “feed Propomi”. |
| **EasyBroker / Wasi** | Similar: SaaS para agencias; API por cuenta de cliente, no agregador país. |

| Aspecto | Estimación |
|---|---|
| Costo | **USD 0–500+/mes** según acuerdo (a veces canje; a veces fee de datos). Impredecible sin cotización. |
| Tiempo | **4–12 semanas** (legal + técnico). |
| Legalidad | **Mejor posición**: dato con permiso. |
| Volumen | Depende del partner: un colegio provincial = **miles–decenas de miles** de avisos de esa provincia; Tokko multi-cuenta podría ser grande pero fragmentado. |

**Pros:** sostenible, alineado a producto B2B.  
**Contras:** lento; no desbloquea ZonaProp de un día para el otro.

---

## Tabla comparativa (resumen)

| Ruta | Costo mensual est. | Puesta en marcha | Riesgo ToS/legal | Volumen adicional potencial | Mantenimiento |
|---|---|---|---|---|---|
| 1 Proxy residencial/API | 50–300+ USD | 3–7 días | Alto (ToS portales) | Alto (nacionales grandes) | Medio |
| 2 Playwright + worker | 14–50 USD infra (+ dev) | 1–3 semanas | Alto | Alto si funciona | Alto (rompe seguido) |
| 3 Acuerdos colegio/Tokko | 0–500+ / canje | 1–3 meses | Bajo–medio | Medio–alto por partner | Bajo |

---

## Recomendación best-effort (no vinculante)

1. **Corto plazo / experimento técnico:** Ruta 1 acotada (1 portal, presupuesto fijo, métrica de % 200 sin challenge) antes de comprometer Ruta 2.  
2. **Mediano plazo / producto:** Ruta 3 con al menos un colegio de las 4 provincias piloto (ya hay relación de facto vía portales oficiales scrapeables).  
3. **Ruta 2** solo si Ruta 1 no alcanza y se acepta costo de mantenimiento de browsers.

La decisión final la toma el dueño del producto.

### Fuentes de contexto usadas
- Evaluaciones curl previas documentadas en `docs/FUENTES_CANDIDATAS.md`.  
- Precios públicos orientativos de ScraperAPI / documentación comercial de proxies residenciales (orden de magnitud, no cotización firmada).  
- Sitios institucionales de colegios (CórdobaProp, MendozaProp, Propia/COCIR).  
- No se realizó contacto comercial real en este encargo.
