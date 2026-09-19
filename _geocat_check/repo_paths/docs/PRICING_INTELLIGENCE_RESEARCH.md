# Pricing intelligence — research (no modelo ML)

## Idea
Dado zona + tipo + ambientes, sugerir rango de precio usando la **mediana**
y percentiles del catálogo actual (misma base que `compute_priority_score`).

## Endpoint entregado (MVP)
`GET /analytics/pricing-hint?zone=Palermo&rooms=2&property_type=Departamento`

Respuesta: `median`, `p25`, `p75`, `sample`, `suggested_range`.

## Limitaciones
- Sesgo al catálogo scrapeado (portales con anti-bot quedan fuera).
- Sin ajuste por m² ni antigüedad del aviso.
- Muestra <3 → no hint.

## Próximos pasos (no en este encargo)
1. Normalizar precio/m² cuando haya `surface`.
2. Ventana temporal (solo avisos vistos en últimos 60d).
3. Comparar con `origin_published_at` para detectar sobreprecio.
