# Entrega: home sin N+1 (frontend)

**Base:** `main` @ `a5e8065` (backend ya con `/properties/random` + group_info)  
**Fecha:** 2026-09-17  
**Archivos:** `apps/web/lib/api.ts`, `apps/web/app/page.tsx`

## Cambio

1. **`getPropertiesRandom(n, filters)`** → `GET /properties/random?n=…` (mismo armado de querystring que `getProperties`; mock: slice de `PROPERTIES`).
2. **`dedupeByGroup(items)`** — dedup local por `listingGroupId`, **sin fetch** (confía en `priceMin`/`priceMax`/`groupMemberCount` del backend).
3. **Carga inicial del home** (`page.tsx` ~97):
   ```ts
   dedupeByGroup(await getPropertiesRandom(30, {operation: 'Venta'}))
   ```
4. **Deep link** `/?property=` sigue con `getProperties({operation:'Venta'})` (catálogo completo a propósito).

## Intactos

- `getPropertiesDeduped` y `getListingGroup` (siguen en el archivo)
- `lib/types.ts`
- Resto de `page.tsx` (offers, modal, tracking)

## git diff --stat (real)

```
 apps/web/app/page.tsx |  4 ++--
 apps/web/lib/api.ts   | 25 +++++++++++++++++++++++++
 2 files changed, 27 insertions(+), 2 deletions(-)
```
