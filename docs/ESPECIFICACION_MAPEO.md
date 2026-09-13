# Mapeo especificación → código (PROPOMI)

Fecha de corte: repo `main` actual.  
Leyenda: **DONE** | **PARTIAL** | **PENDING** | **OUT_OF_SCOPE** (esta tanda)

## Paso 0 — Limpieza

| Ítem | Estado | Notas |
|------|--------|--------|
| Borrar `apps/apps` | **DONE** | No existe en `main` (nada que borrar) |
| Refs en vercel/render/package | **DONE** | `render.yaml` → `apps/api`; web en `apps/web` |
| Script root `dev:api` | **FIXED** | Apuntaba mal; corregido a `cd apps/api && uvicorn app.main:app` |
| `scripts/check.sh` | **NEW** | Puerta DoD: pytest + tsc + next build |

## Paso 1 — Modelo

| Ítem | Estado | Dónde |
|------|--------|--------|
| 1.1 AgencyPhone | **DONE** | `AgencyPhone` + GET/POST `/agencies/{id}/phones` + relink multi-tel |
| 1.2 Property.images[] | **DONE** | JSON list + `migrate_legacy_property_images()` |
| 1.3 detected_at / origin_published_at | **DONE** | Campos en Property; UI usa freshness derivado en API |
| 1.4 verification_status + IG + website + priority | **DONE** | Agency + admin approve/reject |
| 1.5 Subscription **tabla** | **PARTIAL** | Lógica en columnas `Agency.subscription_*` / `plan_lead_quota` — **no** tabla `subscriptions` separada |
| 1.6 LeadCredit **tabla** | **PARTIAL** | `Agency.free_leads_remaining` — **no** tabla `lead_credits` separada |
| 1.7 search_performed | **DONE** | Event en GET `/properties` + analytics/demand + market-opportunities |

## Paso 2 — Backend

| Ítem | Estado |
|------|--------|
| Phones + relink | **DONE** |
| Admin pending/approve/reject | **DONE** (+ reopen, directory) |
| T4.5 solo conteo si no VERIFIED | **DONE** |
| Reveal: free → sub → pay mock | **DONE** |
| GET subscription dedicado | **PENDING** (hoy embebido en GET agency) |
| POST subscription (sin cobro) | **PENDING** |
| market-opportunities | **DONE** |
| POST properties alta manual | **DONE** (`POST /properties`) |
| POST properties/from-url placeholder | **PENDING** |
| Tests T4.5 / multi-phone / search anon | **PARTIAL** (security + t87; ampliar) |

## Paso 3 — Comprador

| Ítem | Estado |
|------|--------|
| Google en OfferModal pantalla 3 | **DONE** (`/auth/google`) |
| OTP comprador | **DONE** (`/auth/otp/verify-buyer`) |
| Autocomplete nombre Google | **DONE** (flujo UI) |

## Paso 4 — Frontend

| Ítem | Estado |
|------|--------|
| types + demo data images | **DONE** / revisar data.ts |
| AgentDashboard PENDING vs VERIFIED | **DONE** |
| IG/web en cuenta | **DONE** |
| Plan/cupo lectura | **PARTIAL** (UI + agency GET; sin POST plan) |
| Admin panel | **DONE** |
| Galería images | **DONE** |
| Market opportunities UI | **DONE** (DemandPanel) |
| Alta manual + multi foto | **DONE** |
| from-url UI | **PENDING** |

## Fuera de esta tanda (no tocar)

| Ítem | Estado |
|------|--------|
| Lemon / pasarela real | **OUT_OF_SCOPE** |
| Crawler | **OUT_OF_SCOPE** |
| Subdominios / tracking origen | **OUT_OF_SCOPE** (código legacy puede existir; no expandir) |
| WhatsApp cold-start auto | **OUT_OF_SCOPE** |

## Deuda estructural (orden real)

1. **Unificar monetización** a tablas `subscriptions` + `lead_credits` (1.5/1.6) con migración desde columnas Agency — un solo punto de “cupo disponible”.
2. **Routers FastAPI** (`admin`, `agencies`, `offers`, `auth`) — `main.py` solo orquesta.
3. **Contrato tipado** (OpenAPI → TS) para no desincronizar Agency/Offer.
4. **POST subscription** + **from-url** placeholder (sin scrape).
5. CI con `scripts/check.sh`.
