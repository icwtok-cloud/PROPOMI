# Scheduler externo (cron-job.org) — antigüedad + crawler

Usar esto si el plan de Render **no soporta** `type: cron` en el Blueprint
(error al aplicar `render.yaml`).

## Variables

| Variable | Valor |
|---|---|
| `API_URL` | URL pública del backend, sin slash final (ej. `https://propomi-api.onrender.com`) |
| `ADMIN_KEY` | mismo valor cargado en el Environment Group de Render |

## Job 1 — expirar antigüedad (diario)

| Campo | Valor |
|---|---|
| URL | `{API_URL}/admin/properties/expire-stale` |
| Método | `POST` |
| Header | `X-Admin-Key: {ADMIN_KEY}` |
| Schedule | todos los días a 04:00 UTC (01:00 Argentina) |
| Body | vacío |

## Job 2 — crawler cada 6 horas

| Campo | Valor |
|---|---|
| URL | `{API_URL}/admin/crawler/run` |
| Método | `POST` |
| Header | `X-Admin-Key: {ADMIN_KEY}` |
| Schedule | cada 6 horas — cron: `0 */6 * * *` |
| Body | vacío |
| Timeout | ≥ 15 minutos |

### Jobs por grupo de fuentes (recomendado en free tier)

Para no saturar un solo request, creá 3 jobs en cron-job.org:

| Job | Schedule (UTC) | URL |
|-----|----------------|-----|
| crawl-ml | `0 0,6,12,18 * * *` | `{API_URL}/admin/crawler/run?sources=mercadolibre` |
| crawl-ar-regionales | `0 1,7,13,19 * * *` | `{API_URL}/admin/crawler/run?sources=cordobaprop,mendozaprop,inmoup,inmoclick,mercado_unico,bienesonline` |
| crawl-py-uy | `0 2,8,14,20 * * *` | `{API_URL}/admin/crawler/run?sources=infocasas_py,infocasas_uy` |

Cada job: método POST, header `X-Admin-Key`, timeout ≥ 15 min.

## Por qué cada 6 horas (no semanal)

Con más provincias en ML/InmoClick y topes de ~200 fichas/fuente, el inventario
acumula por upsert (`source` + `source_url`). Más corridas = más cobertura geo
sin bajar el delay (sigue en 1.0 s para no banear IP).

Con `MAX_AGE_DAYS=90`, un aviso tiene muchas oportunidades de re-crawl antes
de ocultarse.

## Escalado

Si una corrida completa hace timeout del dyno: usá siempre los 3 jobs por
grupo de arriba, nunca un solo job con todas las fuentes a la vez.
