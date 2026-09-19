# README_ENTREGA — Home: pill genérico + grid denser (Airbnb)

## HEAD real de partida

```
1e17a663030582f04b1b935eb558bba422fadbe0
```

`1e17a66 feat(web): wizard comprador a 3 pasos, elimina pantalla de resumen (7.1)`

## git diff --stat real

```
 apps/web/app/globals.css | 19 +++++++++++++++++--
 apps/web/app/page.tsx    | 26 +++++++++++---------------
 2 files changed, 28 insertions(+), 17 deletions(-)
```

## Archivos del hero / pill / tarjeta

| Rol | Archivo |
|-----|---------|
| Hero + pill de búsqueda + listado home | `apps/web/app/page.tsx` |
| Grid del listado (densidad) | `apps/web/app/globals.css` (clase `.properties-grid`) |
| Tarjeta (sin cambios) | `apps/web/components/PropertyCard.tsx` + reglas `.property-card-v2` ya existentes |

No se tocó `PropertyCard.tsx` ni el bloque Airbnb de la tarjeta (~L266–295): el problema era el contenedor de 3 columnas fijas.

## 1. Pill — defaults sin filtro

- `budget`: `'180000'` → `''` (sin tope). El filtro cliente ya usa `Number(budget\|\|Infinity)`.
- Efecto de `getPropertyFilters`: eliminado el default `Buenos Aires`.
- Efecto de `zone`: si `city===''` limpia zona y no autocompleta con `zonesForCity[0]` (evita "El Mirador").
- `budgetLabel` vacío: **"Cualquier presupuesto"** (antes "Presupuesto").
- `whereLabel` vacío ya era **"Cualquier lugar"**; `typeLabel` / `ptype` / `rooms` sin cambios.
- Carga de listado: `getPropertiesDeduped()` sin params de city/budget — no dependía de esos defaults.

## 2. Grid — más columnas

- Listado home (y skeleton) pasan de `className="grid"` a **`properties-grid`**.
- `.properties-grid`: `repeat(auto-fill, minmax(220px, 1fr))` → ~5–6 cols en ~1300px.
- Media 900px: `minmax(180px)`; 620px: `minmax(150px)`.
- **`.grid` global no se toca** (sigue usándose en `tienda/[slug]/page.tsx`).

## Qué NO se tocó

- `AgentDashboard.tsx`, `PropertyCard.tsx`, reglas `.property-card-v2`
- Backend / query params
- Página de detalle

## Archivos en el zip

```
repo_paths/apps/web/app/page.tsx
repo_paths/apps/web/app/globals.css
README_ENTREGA.md
PROGRESS_LOG.md
diff_stat.txt
full_diff.txt
```
