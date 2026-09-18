# México — research crawler (pendiente de validación curl)

Objetivo: sumar inventario MX sin anti-bot pagos ni headless.

## Criterio (igual AR/PY/UY)

1. `robots.txt` legible y no bloquea listados/fichas relevantes
2. Listado HTTP 200 **sin** Cloudflare challenge
3. HTML con hrefs de ficha **o** `__NEXT_DATA__` / JSON-LD
4. Sin login

## Candidatos a probar (orden sugerido)

| Portal | URL listado tentativo | Notas |
|--------|----------------------|--------|
| MercadoLibre MX | `https://inmuebles.mercadolibre.com.mx/casas/venta/...` | Mismo patrón que AR; validar bot wall |
| Inmuebles24 | inmuebles24.com | A menudo anti-bot; verificar |
| Vivanuncios | vivanuncios.com.mx | Validar HTML vs SPA |
| Lamudi MX | lamudi.com.mx | Validar |
| Propiedades.com | propiedades.com | Validar |
| EasyBroker / sitios de franquicia | varía | Muchos SPA |

## Plan de implementación (cuando un portal pase curl)

1. Entrada en `selectors.py` con `enabled=False` hasta validar
2. `queries.py` con estados prioritarios (CDMX, Edomex, Jalisco, NL, Querétaro…)
3. Parser en `parsers/`
4. Tests con fixture HTML real
5. `enabled=True` + job cron `sources=...`

## Estado 2026-09-18

Solo research documentado. **No hay parsers MX en código todavía.**
Prioridad de producto: acumular AR/PY/UY con el scale ya pusheado; MX en la siguiente tanda de research con curl real.
