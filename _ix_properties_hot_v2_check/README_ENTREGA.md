# Entrega v2: `ix_properties_hot` (patch quirúrgico)

**Fecha:** 2026-09-17  
**Problema de la v1:** el zip anterior incluía un `main.py` completo derivado de un HEAD sin `_bulk_group_info` / `_properties_base_stmt` / `GET /properties/random`. Aplicarlo enteros los borraba.

**Esta v2:** solo el diff (+27 líneas). **No incluye** el archivo `main.py` completo a propósito.

## Cambio

```sql
CREATE INDEX IF NOT EXISTS ix_properties_hot
ON properties (hidden_at, last_seen_at, priority_score DESC, detected_at DESC)
WHERE hidden_at IS NULL;
```

Función nueva `ensure_schema_indexes()` + llamada en startup tras `ensure_schema_columns()`.  
No toca `prop_dict`, `_bulk_group_info`, `_properties_base_stmt` ni `/properties/random`.

## git diff --stat (real sobre main @ d9f9f17)

```
 apps/api/app/main.py | 27 +++++++++++++++++++++++++++
 1 file changed, 27 insertions(+)
```

## Cómo aplicar (recomendado)

Sobre tu `main.py` **actual** (el que ya tiene N+1 / random):

```bash
cd PROPOMI
# Opción A — patch (puede requerir -3 si el contexto de blancos difiere)
git apply --3way repo_paths/ix_properties_hot.patch
# o:
patch -p1 < repo_paths/ix_properties_hot.patch
```

Si el patch no aplica por contexto distinto (porque tu main local diverge de GitHub):

1. Abrí `repo_paths/ensure_schema_indexes_snippet.py`
2. Pegá la función `ensure_schema_indexes` **antes** de `migrate_legacy_property_images`
3. Agregá `ensure_schema_indexes()` **justo debajo** de `ensure_schema_columns()` en el bloque de startup

**No reemplaces** todo `main.py` por ningún archivo de entregas anteriores.

## Nota

El `main.py` “actual adjunto” no llegó a este entorno (solo estaban los docx del roadmap). El patch se generó sobre `origin/main` @ `d9f9f17` y es independiente de `_bulk_group_info` (puntos de inserción distintos).
