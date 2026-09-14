# Wildcard DNS — subdominios de agencia (`*.propomi.lat`)

El middleware en `apps/web/middleware.ts` reescribe `https://{slug}.propomi.lat/` → `/tienda/{slug}`.

## Cloudflare

1. Dominio `propomi.lat` en Cloudflare (nameservers del registrador apuntando a CF).
2. DNS → Add record:
   - Type: **CNAME**
   - Name: `*`
   - Target: `cname.vercel-dns.com` (o el que indique Vercel para el proyecto)
   - Proxy: DNS only (gris) o Proxied según guía de Vercel
3. También registro del apex `@` y `www` hacia Vercel.
4. En Vercel → Project → Settings → Domains:
   - Agregar `propomi.lat`
   - Agregar `*.propomi.lat`
5. Env frontend: `NEXT_PUBLIC_ROOT_DOMAIN=propomi.lat`

## Tracking de canal (`origin`)

- Query `?o=` o `?origin=` se guarda en `localStorage` (`propomi-offer-origin`) vía `getOfferOrigin` en `lib/api.ts`.
- Ofertas y leads envían `origin` al backend.
- Links compartibles: `buildShareUrl(propertyId, origin)`.
