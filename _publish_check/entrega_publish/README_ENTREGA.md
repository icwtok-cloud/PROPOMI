# README_ENTREGA — Rediseño "Publicar nueva" + dropdowns geo + alta ciudad con dedup

## HEAD real de partida

```
1e17a663030582f04b1b935eb558bba422fadbe0
```

`1e17a66 feat(web): wizard comprador a 3 pasos, elimina pantalla de resumen (7.1)`

## git diff --stat real

```
 apps/api/app/main.py                   | 130 ++++++++++++++++++++-
 apps/web/app/globals.css               |  37 ++++--
 apps/web/components/AgentDashboard.tsx | 203 +++++++++++++++++++++++----------
 apps/web/lib/api.ts                    |  11 ++
 4 files changed, 307 insertions(+), 74 deletions(-)
```

`geo_catalog.py` **no se modificó**: el merge de `GeoCity` se hace en el endpoint `GET /geo/catalog` (opción permitida por el brief).

## Backend

### Modelo `GeoCity`
- Tabla `geo_cities`: id, country, province, city, normalized, created_by_agency_id, created_at
- UniqueConstraint `(country, province, normalized)`

### `POST /geo/cities` (`require_agent`)
- Body: `{country, province, city, force?}`
- Valida país/provincia contra `GEO_CATALOG` (cerrado)
- Normalización: NFKD → ascii → lower → strip
- Match exacto normalizado (estáticas + DB) → `{created:false, city:<canónico>}`
- Sin exacto y sin `force`: fuzzy `SequenceMatcher` ratio ≥ 0.82 → `{needsConfirmation:true, suggestion}`
- Nuevo o `force:true` → insert → `{created:true, city}`
- Rate-limit: 20/día por agencia (`_rate.check`)

### `GET /geo/catalog`
- Sigue devolviendo países/provincias estáticos
- `citiesByProvince` = estáticas ∪ filas `GeoCity`, ordenadas y deduplicadas

## Frontend

### `AgentDashboard` — "Publicar nueva"
- Chips → `<select>` nativo: País, Provincia, Ciudad, Tipo
- Secciones: Información básica | Ubicación | Precio y superficie | Fotos y descripción
- Grillas 2/3 columnas (1 col en mobile)
- Ciudad: opción `+ Otra ciudad…` → input + Agregar → `addGeoCity`
  - exacto → selecciona canónico
  - similar → notice "¿Quisiste decir X?" con Sí / No (force)
  - nueva → se agrega al estado local del catálogo y queda seleccionada

### CSS (`globals.css`)
- `.publish-section`, `.publish-grid-2/3`, `.publish-field`
- focus `border-color:#BF4E32` (mismo acento que chips activos)
- `border-radius:9px`, padding 11px (alineado a inputs del sitio)
- Media query ≤700px → 1 columna

## Casos de prueba dedup (lógica unitaria)

| Input | Universo | Resultado esperado |
|-------|----------|--------------------|
| `Libertades` | [Libertades, …] | exact → no crea |
| `libertades` / `Libertádes` | idem | exact normalizado → no crea |
| `Libertadez` | Libertades | fuzzy 0.90 ≥ 0.82 → needsConfirmation |
| `Nueva Ciudad XYZ` | sin similares | created:true |
| `Cordoba` vs `Córdoba` | — | ratio 1.0 (exact normalizado) |

## Layout (revisión a ojo)

- Desktop ~1200px: grillas 2 y 3 columnas, secciones con border-top
- Mobile ~375px: media query fuerza 1 columna en `.publish-grid-2/3`

## Qué NO se tocó
- Catálogo de países/provincias (cerrado)
- Zona/barrio texto libre
- submitProperty core, resto del panel
- `geo_catalog.py` estático, `normalize.py`, parsers

## Archivos en el zip

```
repo_paths/apps/api/app/main.py
repo_paths/apps/web/app/globals.css
repo_paths/apps/web/components/AgentDashboard.tsx
repo_paths/apps/web/lib/api.ts
README_ENTREGA.md
PROGRESS_LOG.md
diff_stat.txt
full_diff.txt
```
