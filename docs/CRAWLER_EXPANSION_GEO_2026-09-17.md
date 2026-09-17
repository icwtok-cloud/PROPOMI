# Investigación portales AR / PY / UY (2026-09-17)

Método: curl real (UA desktop) a robots + listado. Criterio scrapeable = HTTP 200 sin Cloudflare/challenge y HTML con hrefs de ficha o JSON embebido (`__NEXT_DATA__` / JSON-LD). Sin headless/JS.

## Ya LIVE en Propomi (no reimplementar)

| Portal | País | Método | Teléfono agente | Notas |
|--------|------|--------|-----------------|-------|
| cordobaprop | AR (Córdoba) | HTML | parcial | enabled |
| mendozaprop | AR (Mendoza) | __NEXT_DATA__ | parcial | enabled |
| mercado_unico | AR (Santa Fe) | HTML homepage | no | enabled |
| mercadolibre | AR multi | JSON-LD | no típico | enabled |
| inmoup | AR (Cuyo) | JSON-LD | parcial | enabled |
| inmoclick | AR multi | HTML | parcial | enabled |
| bienesonline | AR | HTML/JSON-LD | no | enabled |
| infocasas_py | PY | __NEXT_DATA__ | parcial | enabled |
| infocasas_uy | UY | __NEXT_DATA__ | parcial | enabled |

## Triage 2026-09-17 (muestra nacional / cadenas)

| Portal | URL | HTTP | Método viable | Teléfono | Estado |
|--------|-----|------|---------------|----------|--------|
| RE/MAX AR | remax.com.ar/listings/buy | 200 | **SPA vacío** (sin hrefs ficha) | n/d | STANDBY-SPA — requiere headless |
| Century21 AR | century21.com.ar | robots 200; list 404 | n/d | n/d | STANDBY |
| ZonaProp / Adondevivir (Navent) | zonaprop / adondevivir | robots 200; list **403 CF** | — | — | STANDBY-ANTIBOT |
| Argenprop | argenprop.com | robots **405** | — | — | STANDBY-ANTIBOT |
| Properati | properati.com.ar | **401** | — | — | STANDBY-ANTIBOT |
| Gallito UY | gallito.com.uy | robots Allow; list **403 CF** | — | — | STANDBY-ANTIBOT |
| Encuentra24 PY/UY | encuentra24.com/… | 200 | **SPA / poco href ficha** | posible en detalle | STANDBY-SPA |
| MercadoLibre UY/PY | inmuebles.mercadolibre.com.uy/py | 200 pequeño | sin MLA hits en HTML | — | revisar URL exacta / bot wall |
| iCasas AR | icasas.com.ar/venta | 200 | listado categorías; fichas a validar | ? | VIABLE-PENDIENTE (ya hubo parser icasas en tandas previas) |

## Argentina — por jurisdicción (hasta 15 candidatos teóricos)

Convención: **N** = portal nacional con filtro provincia; **L** = local; **C** = cadena.

Para **todas** las 24 unidades AR, los candidatos recurrentes son los mismos N/C (MercadoLibre, InmoClick, iCasas, RE/MAX, Properati, ZonaProp, Argenprop, InfoCasas AR si levantara DNS). Los **L** varían y en curl 2026-09-17 casi todos los agregadores pesados están en **STANDBY-ANTIBOT o SPA**.

| Jurisdicción | Candidatos (nombre · tipo · scrapeable hoy) | # viable real hoy |
|--------------|---------------------------------------------|-------------------|
| CABA / Buenos Aires | ML AR (LIVE), InmoClick (LIVE), ZonaProp (CF), Argenprop (CF), Properati (401), RE/MAX (SPA), iCasas (pendiente), Adondevivir (CF) | 2–3 |
| Córdoba | CórdobaProp (LIVE), ML, InmoClick, RE/MAX SPA, ZonaProp CF | 2–3 |
| Mendoza | InmoUp (LIVE), MendozaProp (LIVE), ML, InmoClick | 3–4 |
| Santa Fe | Mercado Único (LIVE), ML, InmoClick | 2–3 |
| Resto provincias (Catamarca… Tierra del Fuego) | Solo cobertura **N** (ML, InmoClick) + cadenas SPA/CF | **0–2** por provincia |

**Conclusión AR:** no es posible listar 15 portales *scrapeables SSR* por provincia con el stack actual (sin proxy/headless). El techo real está en portales LIVE existentes + 1–2 pendientes; el resto es cola anti-bot/SPA documentada en `FUENTES_CANDIDATAS`.

## Paraguay (17 deptos + Asunción)

| Portal | Cobertura | Scrapeable | Teléfono |
|--------|-----------|------------|----------|
| InfoCasas PY | nacional | **LIVE** | a veces en ficha |
| Encuentra24 PY | nacional | STANDBY-SPA | posible |
| ML PY | nacional | a validar | raro |
| Portales puramente departamentales | muy escasos online | — | — |

Por departamento: la cobertura real hoy es **InfoCasas PY** (multi-depto). No hay 15 SSR locales por depto.

## Uruguay (19 deptos)

| Portal | Cobertura | Scrapeable | Teléfono |
|--------|-----------|------------|----------|
| InfoCasas UY | nacional | **LIVE** | a veces |
| Gallito | nacional | **CF 403** | — |
| Encuentra24 UY | nacional | STANDBY-SPA | posible |
| ML UY | nacional | a validar | raro |

## Cadenas (RE/MAX y equivalentes)

Condición brief: teléfono obligatorio para cargar.

| Cadena | Sitio | Barrera | Teléfono en ficha |
|--------|-------|---------|-------------------|
| RE/MAX AR | remax.com.ar | SPA (Angular/React shell sin fichas en HTML) | n/d sin headless |
| Century21 AR | century21.com.ar | listados no resueltos | n/d |

**No se implementó parser RE/MAX** en esta entrega: no hay HTML de ficha extraíble sin infraestructura anti-bot/headless (fuera de alcance de este crawler).

## Dedup reforzado (esta entrega)

Señal: `country|city|zone|title/address norm|price//2500|surface//3|rooms|type` (in-run) + match DB cross-source en `upsert_payload` (city+country+price±8%+rooms+type → mismo `listing_group_id`).

## Teléfono / claim

Campo: `Property.contact_phone_raw` + `contact_phone_normalized` (vía `normalize_phone` en main).  
`relink_properties(db, agency_id, phone)` matchea `contact_phone_normalized == phone` del login OTP.  
Pipeline crawler: si el parser llena `RawListing.agency_phone`, ahora se persiste (antes se forzaba `None`).
