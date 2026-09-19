# PROGRESS_LOG

## 2026-09-17

1. Clonado `main` de https://github.com/icwtok-cloud/PROPOMI (depth 1) → HEAD `2b8580ac7e12f69e0466addc576dfa422f0dfd75`.
2. Confirmado 593 × U+FFFD en 387 líneas de `apps/api/app/main.py` (lectura de bytes / count Python).
3. Extracción de todas las líneas afectadas y contextos.
4. Reconstrucción manual por contexto (español rioplatense / argentino): vocales acentuadas, ñ, em-dashes, signos de interrogación/exclamación donde correspondía.
5. Aplicación de reemplazos exactos (lista ordenada de strings corruptos → correctos). Iteraciones hasta residual = 0.
6. Verificación final:
   - `chr(0xFFFD)` count = 0
   - `git diff --stat` = 387 insertions / 387 deletions, solo main.py
   - Mensajes de error HTTPException revisados (Ingresá, Sesión, Verificá, válido, teléfono, código, etc.)
7. Empaquetado en estructura `repo_paths/...` + README + listado completo + diff.

No se tocó ninguna otra lógica, import, espaciado ni línea no afectada.

## 2026-09-17 — Catálogo geo completo + sin alta manual de ciudad (BRIEF)

- Confirmado HEAD `501fb5c` posterior a commits de Publicar nueva / GeoCity y alineación de tarjetas.
- Reemplazado `geo_catalog.py` por carga de `geo_data/{ar,py,uy}.json` generados desde:
  - AR: Georef/BAHRA (localidades.json) → 3866 localidades / 24 provincias.
  - PY/UY: GeoNames dumps filtrados (PPL*) → 4365 / 1008 localidades.
- Eliminado flujo “+ Otra ciudad…” y todo el bloque de input/confirmación en `AgentDashboard.tsx`.
- `POST /geo/cities` y `GeoCity` dejados intactos (huérfanos respecto del formulario de agente).
- Entregables: README_ENTREGA.md + este log + zip con repo_paths.
