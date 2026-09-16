# Fuentes candidatas v2 — AR nacional + Paraguay + Uruguay

Fecha triage: **2026-09-16**. Metodología: curl robots.txt + listado + ficha (SSR/JSON-LD/__NEXT_DATA__ vs SPA/anti-bot).

> **Tanda 1** de este encargo: implementadas las fuentes con HTML real + fixture + test.
> El techo de “15 por país” **no** se alcanza sin anti-bot o más tandas; se documenta el techo real.

## Resumen por país

| País | enabled=True (esta tanda + previas) | Cola anti-bot / no viable (tanda 1) |
|------|--------------------------------------|-------------------------------------|
| **Argentina** | Previas: cordobaprop, mendozaprop, mercado_unico, mercadolibre, inmoup, inmoclick. **Nueva:** bienesonline | nestoria (401), remax_ar (SPA), infocasas_ar (DNS), century21_ar (URL listado pendiente) |
| **Paraguay** | **infocasas_py** | remax_py (listado vacío) |
| **Uruguay** | **infocasas_uy** | gallito_uy (CF 403), remax_uy (asumido SPA) |

## Argentina

| Fuente | Cobertura | enabled | Patrón / bloqueo | Volumen (est.) |
|--------|-----------|---------|------------------|----------------|
| cordobaprop | Córdoba | True | HTML listado | regional |
| mendozaprop | Mendoza | True | __NEXT_DATA__ | regional |
| mercado_unico | Mendoza/Cuyo | True | NUXT/og | regional |
| mercadolibre | multi-prov | True | JSON-LD | alto |
| inmoup | Mendoza/Cuyo | True | JSON-LD | ~25k |
| inmoclick | multi-prov | True | /ficha/ | alto |
| **bienesonline** | **AR multi-prov (bienesonline.ai)** | **True** | **JSON-LD RealEstateListing** | medio |
| remax_ar | nacional | False | SPA shell sin fichas | — |
| nestoria_ar | nacional | False | robots 401 Access Denied | — |
| infocasas_ar | nacional | False | DNS no resuelve (2026-09-16) | — |
| century21_ar | nacional | False | /propiedades 404; listado no hallado | — |
| zonaprop / argenprop / properati | — | False | CF / AWS ELB (previo) | — |

## Paraguay

| Fuente | Cobertura | enabled | Patrón / bloqueo | Volumen (est.) |
|--------|-----------|---------|------------------|----------------|
| **infocasas_py** | **país** | **True** | **__NEXT_DATA__ pageProps.data** | alto (marketplace) |
| remax_py | país | False | robots OK; listado ~2.5KB sin fichas | — |

## Uruguay

| Fuente | Cobertura | enabled | Patrón / bloqueo | Volumen (est.) |
|--------|-----------|---------|------------------|----------------|
| **infocasas_uy** | **país** | **True** | **mismo backend InfoCasas** | alto |
| gallito_uy | país | False | listado 403 Cloudflare challenge | — |
| remax_uy | país | False | robots OK; SPA probable (como AR) | — |
| mercadolibre UY | país | — | listado 200 pero HTML mínimo sin hrefs `_JM` en triage | re-eval |

## Cola anti-bot (detalle de borde)

| Fuente | Tipo de bloqueo |
|--------|-----------------|
| gallito.com.uy/inmuebles | Cloudflare challenge (403) |
| nestoria.com.ar | 401 Access Denied en robots |
| zonaprop / argenprop | Cloudflare challenge (histórico) |
| properati | AWS ELB 403 (histórico) |

## Próximas tandas sugeridas
1. Re-eval InfoCasas AR cuando DNS responda; Century21 URL real de listado.
2. Más portales PY/UY (clasificados locales, Facebook no aplica).
3. SPA nacionales solo si hay decisión anti-bot (docs/ANTIBOT_PROPUESTA.md).
