# Entrega — Catálogo geográfico completo + quitar alta manual de ciudad

**Repo base:** https://github.com/icwtok-cloud/PROPOMI  
**Rama:** `main`  
**HEAD confirmado:** `501fb5c` (`fix(web): alinear alturas de tarjetas del listado…`)  
Posterior a `82a3aa6` (feat Publicar nueva + GeoCity/POST `/geo/cities`) y al fix de alineación de tarjetas.

## Resumen del cambio

1. **Catálogo geográfico exhaustivo**  
   Se reemplazó el diccionario “razonable, no exhaustivo” de `geo_catalog.py` por datasets completos de localidades oficiales / abiertas para Argentina, Paraguay y Uruguay.  
   Estructura de datos **igual** (`dict[str, list[str]]` por país → provincia/departamento → lista de ciudades), por lo que `GET /geo/catalog` y el resto de consumidores no requieren cambios de contrato.

2. **Frontend**  
   En `AgentDashboard.tsx` se eliminó por completo el flujo “+ Otra ciudad…” (select option, bloque de input, botón “Agregar ciudad”, estados y `confirmOtherCity`).  
   El `<select>` de Ciudad lista **únicamente** las localidades del catálogo para el par País + Provincia/Departamento elegido.  
   Zona/barrio sigue siendo texto libre (fuera de alcance).

3. **Backend**  
   `POST /geo/cities` y el modelo `GeoCity` se dejaron **intactos** en `main.py`. Quedan huérfanos respecto del formulario de agente (sin consumidor en el frontend). Útiles a futuro para admin/soporte.

## Fuentes del dataset (trazabilidad)

| País       | Fuente | Versión / fecha | Licencia | Entradas |
|------------|--------|-----------------|----------|----------|
| **Argentina** | Georef API (datos.gob.ar) — recurso `/localidades` basado en **BAHRA** (Base de Asentamientos Humanos de la República Argentina) + INDEC | Descarga 2026-09-17 de `https://apis.datos.gob.ar/georef/api/v2.0/localidades.json` (4028 registros → 3866 nombres únicos tras dedup por provincia) | Datos abiertos del Estado argentino (uso libre con atribución a la fuente) | 24 provincias/CABA · **3866** localidades |
| **Paraguay** | GeoNames country dump `PY.zip` (feature class P, códigos PPL/PPLA*/PPLC/…) | Dump 2026-09-17 | Creative Commons Attribution 4.0 (CC-BY 4.0) — atribuir a GeoNames | 18 departamentos · **4365** localidades |
| **Uruguay** | GeoNames country dump `UY.zip` (mismos filtros) | Dump 2026-09-17 | CC-BY 4.0 — atribuir a GeoNames | 19 departamentos · **1008** localidades |

**Nota AR:** se normalizaron nombres de provincia (`Ciudad Autónoma de Buenos Aires` → `CABA`; nombre largo de Tierra del Fuego → `Tierra del Fuego`) para mantener compatibilidad con el resto del código y con el catálogo anterior.

**Ejemplo que fallaba antes:** “Esperanza” (Santa Fe, cabecera de Las Colonias) ahora está presente en el catálogo.

## Cambio de estructura de archivos

Los diccionarios ya no van inline (el archivo sería de ~200 KB+ de texto).  
Datos en:

```
apps/api/app/geo_data/
  ar.json   (~63 KB, 24 provincias, 3866 localidades)
  py.json   (~87 KB, 18 departamentos, 4365 localidades)
  uy.json   (~17 KB, 19 departamentos, 1008 localidades)
```

`geo_catalog.py` solo carga los JSON y expone `get_geo_catalog()` / `GEO_CATALOG` con la misma forma de siempre.

## Qué queda huérfano (explícito)

- Endpoint `POST /geo/cities` + modelo `GeoCity` + lógica de dedup/sugerencia en `main.py`: **sin consumidor en el frontend** del agente. No se borra.
- Función `addGeoCity` en `apps/web/lib/api.ts`: sigue exportada (por si se reutiliza); el import y el uso se quitaron de `AgentDashboard.tsx`.

## Diff real (`git diff --stat`)

```
 apps/api/app/geo_catalog.py            | 114 +++++++--------------------------
 apps/web/components/AgentDashboard.tsx |  73 ++-------------------
 2 files changed, 23 insertions(+), 164 deletions(-)
```

+ archivos nuevos no trackeados: `apps/api/app/geo_data/{ar,py,uy}.json`

## Cómo verificar

```bash
# desde raíz del repo
python -c "
from apps.api.app.geo_catalog import get_geo_catalog
c = get_geo_catalog()
assert 'Esperanza' in c['citiesByProvince']['Argentina|Santa Fe']
print('OK — Esperanza presente; total AR cities', sum(len(v) for v in c['citiesByProvince'].values() if v and 'Argentina' in str(v)))
"
# o levantar la API y GET /geo/catalog
```

## Fuera de alcance (confirmado)

- Flujo de Zona/barrio (texto libre).
- Resto de “Publicar nueva” (secciones, precio/superficie, fotos).
- Alineación de tarjetas (ya en HEAD).
- Casos residuales de localidades que no aparezcan ni en BAHRA/GeoNames (no se reintroduce alta manual).
