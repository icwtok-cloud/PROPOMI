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

## Job 2 — crawler semanal

| Campo | Valor |
|---|---|
| URL | `{API_URL}/admin/crawler/run` |
| Método | `POST` |
| Header | `X-Admin-Key: {ADMIN_KEY}` |
| Schedule | lunes 05:00 UTC (02:00 Argentina) |
| Body | vacío (opcional query `?sources=cordobaprop,inmoup,mendozaprop,mercado_unico`) |
| Timeout | ≥ 10 minutos (el crawl con delay 1s puede tardar) |

## Por qué 7 días el crawler

Con `MAX_AGE_DAYS=60`, un aviso tiene ~8–9 oportunidades de ser re-visto
antes de ocultarse. Suficiente margen si una corrida falla.
