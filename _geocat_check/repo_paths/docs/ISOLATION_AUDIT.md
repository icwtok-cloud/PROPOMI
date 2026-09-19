# Auditoría de aislamiento multi-tenant (agencias)

Fecha: 2026-09-15

## Endpoints revisados

| Endpoint | Filtro | Estado |
|---|---|---|
| GET /leads | agency via property_ids propios + listing_group | OK |
| GET /offers | idem | OK |
| GET /agencies/{id}/opportunities | `session.agency_id == agency_id` | OK |
| GET /agencies/{id}/market-opportunities | idem | OK |
| GET /agencies/{id} y PATCH | idem | OK |
| POST /agencies/{id}/phones | 403 si no es tuya | OK (tests) |
| GET /events/funnel | **antes: global** → ahora filtra `Event.agency_id` | **CORREGIDO** |
| GET /analytics/summary | **antes: counts globales** → ahora por agencia | **CORREGIDO** |
| GET /analytics/demand | agregado anónimo global (by design) | OK documentado |
| GET /analytics/supply-demand | demanda global + oferta catálogo (by design) | OK |
| GET /properties | público / filtros; agency_id query es filtro no ownership | OK (público) |

## Huecos grandes (no tocados a medias)
Ninguno crítico restante tras el fix de funnel/summary. El listing_group
permite ver leads de propiedades del mismo grupo aunque agency_id difiera
(decisión de producto explícita T87) — no es fuga cross-tenant arbitraria.
