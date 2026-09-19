# Almacenamiento de imágenes (research)

**Estado actual:** `Property.images` es `list[str]` de URLs externas del portal
origen (ZonaProp CDN, ML, InmoUp, etc.). El crawler no descarga bytes.

**Problema futuro:** cuando una agencia suba fotos vía `POST /properties` o
`/properties/ingest` propio, necesitamos storage durable (no hotlink a WhatsApp
o drive del agente).

## Opciones evaluadas

| Opción | Pros | Contras | Costo aprox. |
|---|---|---|---|
| **Cloudflare R2** | S3-compat, sin egress fee, ya usamos CF | Setup bucket + token | ~$0.015/GB/mes |
| AWS S3 | Maduro, SDK ubicuo | Egress caro fuera de AWS | similar + egress |
| Vercel Blob | Simple si front en Vercel | Vendor lock, límites plan | plan-dependent |
| Guardar solo URLs | Cero infra | Links se rompen; no control | $0 |

## Propuesta simple (fase 1)

1. Bucket R2 `propomi-images` (público read via custom domain o r2.dev).
2. Endpoint `POST /properties/{id}/images` (agent auth): recibe multipart,
   valida tipo/size (jpeg/webp ≤ 3 MB, máx 5), sube a
   `agencies/{agency_id}/{property_id}/{uuid}.webp`, append URL a
   `Property.images`.
3. Al crawlear: **seguir con URLs externas** (no rehost masivo — costo y ToS).
4. Thumbnail opcional con CF Image Resizing en el front.

## No implementar en este encargo

Solo research. Implementar cuando el primer flujo de carga de agencia esté
en el roadmap de producto.
