# Entrega: N+1 listing group + GET /properties/random

**Base:** `main` @ `46489e3` (ya incluye `ix_properties_hot` / `ensure_schema_indexes`)  
**Fecha:** 2026-09-17  
**Archivo:** solo `apps/api/app/main.py`

## Qué se agregó

1. **`prop_dict(p, group_info=None)`** — si `group_info` no es `None`, incluye `priceMin` / `priceMax` / `groupMemberCount`. Callers sin `group_info` (p.ej. `GET /properties/{id}/group`) sin cambios de formato.
2. **`_bulk_group_info(db, props)`** — una sola query `GROUP BY listing_group_id` (min/max/count) para toda la página → elimina el N+1 del home.
3. **`_properties_base_stmt(...)`** — mismos filtros que tenía inline `GET /properties` (incluye `city=="Sin descripción"`, hidden, freshness).
4. **`GET /properties`** — usa base stmt + `order_by(priority_score, detected_at)` + bulk group en cada `prop_dict`. **Conserva** `Event(search_performed)`.
5. **`GET /properties/random?n=30`** — mismos filtros, `ORDER BY random() LIMIT n` en SQL, `n` clamp 1–60. **Sin** `search_performed`.

## Qué no se tocó

- `GET /properties/{id}/group`
- `ensure_schema_indexes` / `ix_properties_hot`
- Evento `search_performed` de `/properties`

## git diff --stat (real)

```
 apps/api/app/main.py | 192 +++++++++++++++++++++++++++++++++++++++++----------
 1 file changed, 156 insertions(+), 36 deletions(-)
```

## Aplicar

Copiar `repo_paths/apps/api/app/main.py` sobre el clone en `46489e3` (o main actual con el índice).  
Ruta `/properties/random` queda **antes** de `/properties/{property_id}` para no colisionar.

## Frontend (sugerido, fuera de este diff)

Home inicial → `GET /properties/random?n=30` en lugar de `/properties` + N llamadas a `/group`.
