# README_ENTREGA — MAX_AGE_DAYS=90 + parse_origin_date + origin en parsers

## HEAD real de partida

```
1e17a663030582f04b1b935eb558bba422fadbe0
```

`1e17a66 feat(web): wizard comprador a 3 pasos, elimina pantalla de resumen (7.1)`

## git diff --stat real

```
 apps/api/app/crawler/normalize.py            | 38 ++++++++++++++++++++++++++++
 apps/api/app/crawler/parsers/argenprop.py    | 13 ++++++++++
 apps/api/app/crawler/parsers/bienesonline.py | 12 +++++++++
 apps/api/app/crawler/parsers/infocasas.py    | 11 ++++++++
 apps/api/app/crawler/parsers/mercadolibre.py | 18 +++++++++++++
 apps/api/app/crawler/parsers/zonaprop.py     | 26 +++++++++++++++++++
 apps/api/app/crawler/runner.py               | 19 ++++++++++++--
 7 files changed, 135 insertions(+), 2 deletions(-)
```

## Parte A — Filtro 90 días

1. `MAX_AGE_DAYS`: **60 → 90** en `runner.py`.
2. `parse_origin_date(raw)` en `normalize.py`:
   - ISO 8601 (`YYYY-MM-DD`, con hora, `Z`/offset)
   - `dd/mm/aaaa` y `dd-mm-aaaa`
   - Devuelve `None` sin excepción si vacío / no reconocido
3. En `upsert_payload`, **solo rama de creación** (no updates):
   - Si `origin_published_at` parseable y edad > 90 días → `return "skipped"` + `logger.info`
   - Si fecha ausente o no parseable → **no descarta** (pasa igual)

No toca filas ya existentes en DB.

### Casos de prueba `parse_origin_date`

| Input | Resultado |
|-------|-----------|
| `2026-09-01` | datetime UTC |
| `2026-09-01T00:00:00` | datetime UTC |
| `2026-09-01T12:30:00Z` | datetime UTC |
| `01/09/2026` | 2026-09-01 UTC |
| `01-09-2026` | 2026-09-01 UTC |
| `""` | `None` |
| `None` | `None` |
| `"not a date"` / `"hace 3 dias"` | `None` (sin excepción) |

## Parte B — origin_published_at en parsers

| Fuente | Qué se hizo | Nota |
|--------|-------------|------|
| **cordobaprop** | Ya llenaba (`Fecha de ingreso`) | Sin cambios |
| **zonaprop** | `datePublished`/`dateModified`/`dateCreated` del JSON-LD + meta `article:published_time` / regex en HTML | Si el portal no expone la fecha, queda vacío |
| **mercadolibre** | JSON-LD Product + melidata `start_time`/`date_created` | Idem |
| **argenprop** | meta `article:published_time`, `"datePublished"`, patrón `Publicado el dd/mm/aaaa` | HTML semántico; si no hay match → vacío |
| **infocasas** | keys `published_at`/`createdAt`/etc. en `__NEXT_DATA__.pageProps.data` | Si InfoCasas no manda esos keys → vacío |
| **bienesonline** | `datePublished`/`dateModified`/`dateCreated` en JSON-LD listing/place/offer | Idem |

**Limitación documentada:** si una fuente **no publica** la fecha en el HTML, seguirá sin `origin_published_at` y caerá en “score medio” de recencia. El filtro de 90 días **no las descarta** (ausencia ≠ antigüedad). Fuentes candidatas a seguir sin fecha real hasta confirmar HTML en producción: cualquier portal que no exponga ISO/`datePublished` en el markup que ya leemos.

## Qué NO se tocó

- `compute_priority_score`
- `geo_catalog.py`, `main.py`, `apps/web`
- Límites de cortesía del crawler

## Archivos en el zip

```
repo_paths/apps/api/app/crawler/runner.py
repo_paths/apps/api/app/crawler/normalize.py
repo_paths/apps/api/app/crawler/parsers/{zonaprop,argenprop,mercadolibre,infocasas,bienesonline}.py
README_ENTREGA.md
PROGRESS_LOG.md
diff_stat.txt
full_diff.txt
```
