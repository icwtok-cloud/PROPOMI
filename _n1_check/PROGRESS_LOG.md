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

## 2026-09-17 — N+1 listing group + /properties/random

- `prop_dict(..., group_info=None)` con priceMin/priceMax/groupMemberCount opcionales.
- `_bulk_group_info`: 1 query agregada por página (fin del N+1 home → /group).
- `_properties_base_stmt`: filtros compartidos.
- `GET /properties` refactor + bulk; search_performed intacto.
- `GET /properties/random` (n≤60, ORDER BY random() en SQL, sin search_performed).
- Base: 46489e3 (ix_properties_hot ya presente). No se tocó el índice ni /group.
