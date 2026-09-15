# Fuentes candidatas del crawler — investigación 2026-09-15

Criterio: volumen local por provincia > notoriedad nacional. Veredicto
basado en robots.txt + HTML real (no solo robots). Los 7 portales ya en
`selectors.py` se reutilizan sin reinvestigar desde cero.

## Resumen ejecutivo

| Veredicto | Fuentes |
|---|---|
| **HABILITAR (enabled=True)** | `cordobaprop`, `inmoup` |
| **PENDIENTE** (robots OK / parser existe, HTML listado SPA o sin prueba completa) | `mendozaprop`, `mercado_unico`, `propia` |
| **DESCARTADO / bloqueado borde** | `zonaprop`, `argenprop`, `mercadolibre`, `properati` + la mayoría de nacionales grandes |

**Señal de producto:** entre ~40 dominios evaluados, solo 2 fuentes
habilitables sin anti-bot. Ampliar catálogo nacional requiere proxy/anti-bot
o aceptar foco regional (Córdoba + Mendoza/Cuyo).

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
| Mercado Único | mercado-unico.com | regional | Allow:/ | SPA; links ficha no en HTML listado | **PENDIENTE** — parser existe; listado no expone hrefs estáticos |
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
| MendozaProp | mendozaprop.com | provincia (CCPIM) | 404 (sin robots = sin restricción declarada) | SPA; listado sin hrefs estáticos | **PENDIENTE** — parser previo existe; falta extractor de links real |
| ZonaProp / etc. | nacional | — | bloqueados | — | **DESCARTADO** |
| Portal by Alanna | (Valle de Uco) | local chico | no medido | — | **DESCARTADO** — volumen bajo |

## Notas de método

- `curl -I` / `curl -L` con UA de bot y browser; se registró 403/challenge vs 200.
- “SPA” = contenido de fichas no aparece en el HTML del listado sin ejecutar JS → parser de detalle posible, discovery de URLs no.
- No se reintentaron portales ya documentados como 403 en el encargo anterior sin evidencia de cambio.
