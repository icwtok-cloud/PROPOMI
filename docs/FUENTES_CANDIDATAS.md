# Fuentes candidatas del crawler — investigación 2026-09-15

Criterio: volumen local por provincia > notoriedad nacional. Veredicto
basado en robots.txt + HTML real (no solo robots). Los 7 portales ya en
`selectors.py` se reutilizan sin reinvestigar desde cero.

## Resumen ejecutivo

| Veredicto | Fuentes |
|---|---|
| **HABILITAR (enabled=True)** | `cordobaprop`, `inmoup`, **`mendozaprop`**, **`mercado_unico`** |
| **PENDIENTE** | `propia` (Nuxt SPA sin hrefs de ficha en listado) |
| **DESCARTADO / bloqueado borde** | `zonaprop`, `argenprop`, `mercadolibre`, `properati` |

**Actualización 2026-09-15 (encargo #3):** mendozaprop habilitado vía
sitemap.xml (solo `/venta-*`) + `__NEXT_DATA__`. mercado_unico habilitado
vía homepage (links `/propiedades/{ObjectId}`) + NUXT/og. Crons de antigüedad
y crawler activos en `render.yaml`; fallback documentado en
`docs/CRON_EXTERNO.md`.

---

## Buenos Aires (CABA + GBA)

| Nombre | URL base | Alcance | robots.txt | Estructura | Veredicto |
|---|---|---|---|---|---|
| ZonaProp | zonaprop.com.ar | nacional | permite fichas + pag 2-5 | JSON embebido | **DESCARTADO** — Cloudflare challenge en listados/fichas (2026-09-15) |
| Argenprop | argenprop.com | nacional | 403 CloudFront en robots | — | **DESCARTADO** — bot protection borde |
| MercadoLibre Inmuebles | inmuebles.mercadolibre.com.ar | nacional | 403 en robots | — | **DESCARTADO** — bot protection |
| Properati | properati.com.ar | nacional (foco CABA) | 403 AWS ELB | — | **DESCARTADO** — bot protection |
| Roomix | roomix.ai | nacional (agregador) | no evaluado a fondo | agregador/IA | **PENDIENTE** — es metabuscador; riesgo de ToS y duplicados |
| BuscadorProp | buscadorprop.com.ar | nacional | no medido | meta | **PENDIENTE** — meta, bajo valor incremental |
| RE/MAX AR | remax.com.ar | red franquicias | no medido | — | **PENDIENTE** — stock por franquicia, no portal masivo |
| Solo Dueños / Bullano | soloduenos.com / bullano.com.ar | dueño directo | no medido | — | **PENDIENTE** — volumen bajo vs. portales |
| iCasas / GoPlaceIt | icasas.com.ar | residual | no medido | — | **DESCARTADO** — volumen irrelevante 2026 |

## Córdoba

| Nombre | URL base | Alcance | robots.txt | Estructura | Veredicto |
|---|---|---|---|---|---|
| CordobaProp | cordobaprop.com | provincia (CPI) | Allow:/ (admin/api bloqueados) | JSON embebido | **HABILITAR** — ya enabled=True, único live del piloto previo |
| ZonaProp / Argenprop / ML | (nacional) | — | ver BA | — | **DESCARTADO** (mismo bloqueo) |
| Mercado Único | mercado-unico.com | regional (Santa Fe fuerte) | Allow:/ | homepage + NUXT/og | **HABILITAR** — enabled=True 2026-09-15 (discovery por homepage) |
| La Voz clasificados | lavoz.com.ar | medio local | no medido | clasificados | **PENDIENTE** — no es portal inmobiliario puro |
| InmoRadar | inmoradar.tech | analytics CBA | — | no listados públicos | **DESCARTADO** — producto B2B analytics, no stock scrapeable |
| Portales de inmobiliarias sueltas | proactiva, caffaratti, etc. | 1 agencia | — | — | **DESCARTADO** — volumen insuficiente |

## Santa Fe (Rosario + región)

| Nombre | URL base | Alcance | robots.txt | Estructura | Veredicto |
|---|---|---|---|---|---|
| Propia (COCIR) | propia.com.ar | sur Santa Fe / Rosario (~70k avisos declarados) | Allow:/ (CF managed, ai-train=no) | Nuxt SPA; listado sin hrefs de ficha en HTML inicial | **PENDIENTE** — HTML 200 sin challenge; requiere API/JS o reverse del Nuxt payload. Alto valor regional si se resuelve |
| ZonaProp / Argenprop / ML | nacional | — | bloqueados | — | **DESCARTADO** |
| Portales de agencias (Porta, etc.) | varios | 1 agencia | — | — | **DESCARTADO** — volumen bajo |

## Mendoza (y Cuyo)

| Nombre | URL base | Alcance | robots.txt | Estructura | Veredicto |
|---|---|---|---|---|---|
| InmoUp | inmoup.com.ar | Cuyo (Mza/SJ/SL), ~25k avisos | Allow general; bloquea /panel /json maps | JSON-LD schema.org RealEstateListing | **HABILITAR** — HTML 200 real, parser + fixture + test (2026-09-15) |
| MendozaProp | mendozaprop.com | provincia (CCPIM) | 404 (sin restricción) | sitemap + `__NEXT_DATA__` | **HABILITAR** — enabled=True 2026-09-15 |
| ZonaProp / etc. | nacional | — | bloqueados | — | **DESCARTADO** |
| Portal by Alanna | (Valle de Uco) | local chico | no medido | — | **DESCARTADO** — volumen bajo |

## Notas de método

- `curl -I` / `curl -L` con UA de bot y browser; se registró 403/challenge vs 200.
- “SPA” = contenido de fichas no aparece en el HTML del listado sin ejecutar JS → parser de detalle posible, discovery de URLs no.
- No se reintentaron portales ya documentados como 403 en el encargo anterior sin evidencia de cambio.
