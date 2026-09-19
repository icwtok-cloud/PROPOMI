# README_ENTREGA — Alinear alturas de tarjetas del listado home

## HEAD real de partida

```
82a3aa62b2e1473376aa53546987e07fcf737e47
```

`82a3aa6 feat(web+api): rediseno Publicar nueva (selects+secciones) + GeoCity con dedup`

(Posterior a `703a336` home sin defaults + grid densidad.)

## git diff --stat real

```
 apps/web/app/globals.css             | 23 ++++++++++++++++++-----
 apps/web/components/PropertyCard.tsx | 16 +++++++++-------
 2 files changed, 27 insertions(+), 12 deletions(-)
```

## Cambios

### `globals.css` — `.property-card-v2`
- `display:flex; flex-direction:column; height:100%` (usa la altura que el grid estira)
- `.pbody` / `.body`: `display:flex; flex-direction:column; flex:1`
- `.actions`: `margin-top:auto` → botones al fondo de la tarjeta
- `.pcard-title`: ya tenía `nowrap` + ellipsis (1 línea) — se mantiene
- `.pcard-subtitle` y `.specs`: 1 línea con ellipsis
- Foto (`aspect-ratio:4/3`, `max-height:180px`) y `.properties-grid` **sin cambios**

### `PropertyCard.tsx`
- `.tags` solo se renderiza si hay al menos un flag true (`parking|balcony|credit|pool|petFriendly`)

## Qué NO se tocó
- Favoritos, comparar, badges, datos
- `.properties-grid`, tamaño de foto

## Archivos en el zip

```
repo_paths/apps/web/app/globals.css
repo_paths/apps/web/components/PropertyCard.tsx
README_ENTREGA.md
PROGRESS_LOG.md
diff_stat.txt
full_diff.txt
```
