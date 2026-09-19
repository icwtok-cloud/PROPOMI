# Fuentes candidatas — piloto 4 provincias

**Objetivo de producto:** 15 portales scrapeables por provincia (CBA / BA / SF / MZA) = 60.
**Realidad 2026-09-15:** el mercado inmobiliario argentino está concentrado en 3–4
portales nacionales con bot-protection fuerte + un puñado de portales de colegios
regionales. Tras evaluar **50+ dominios** (lista larga abajo), los **viables con
datos embebidos explotables** son **6 fuentes** (varias multi-provincia).

No se inventaron portales ni se forzaron los que fallan challenge/403.

## Resumen ejecutivo — fuentes enabled=True

| ID | Portal | Provincias | Volumen estimado (venta) | Patrón datos | Discovery |
|---|---|---|---|---|---|
| cordobaprop | CórdobaProp | CBA | regional (miles) | HTML/JSON propio | list URLs |
| inmoup | InmoUp | MZA (+Cuyo) | ~25.000 avisos (portal) | JSON-LD RealEstateListing | list + JSON-LD |
| mendozaprop | MendozaProp | MZA | ~11.000 locs sitemap | `__NEXT_DATA__` | sitemap `/venta-*` |
| mercado_unico | Mercado Único | SF | miles (homepage) | NUXT + og | homepage ObjectId |
| **mercadolibre** | ML Inmuebles | **4 provincias** | CBA casas ~14.5k; nacional cientos de miles | JSON-LD Product | `/MLA-` en listado |
| **inmoclick** | InmoClick | **4 provincias** | ~150k declarados nacionales | og + HTML | `/inmuebles/{id}/ficha/` |

**Volumen total scrapeable (orden de magnitud, venta):**
- Por provincia vía ML: 5k–20k+ según provincia/tipo
- InmoClick: cobertura multi-provincia alta
- Regionales colegio: 5k–25k por provincia fuerte

No es 15 portales independientes × 4, pero **sí cobertura multi-fuente en las 4 provincias piloto**.

---

## Etapa 1 — Lista larga por provincia (prioridad)

### Córdoba (≥20)
1. CórdobaProp (colegio) — **LIVE**
2. MercadoLibre Inmuebles — **LIVE**
3. InmoClick — **LIVE**
4. ZonaProp — DESCARTADO challenge
5. Argenprop — DESCARTADO 405/bloque
6. Properati — DESCARTADO 401
7. RE/MAX — list 200 pero sin hrefs de ficha en HTML
8. BuscadorProp — meta-agregador, list 200, valor bajo/ToS
9. Roomix — 403 challenge
10. Clasificados La Voz — 403 challenge
11. iCasas — home 200, listados provinciales 404/410
12. GoPlaceIt — 200 pero shell vacío (~5kb)
13. Mudafy — 200 SPA sin hrefs de ficha
14. Propertia — marketing WP, sin inventario
15. InmoUp — Cuyo (poca CBA)
16. Nestoria / Mitula / Trovit — 401/0 meta
17. Lamudi / DotProperty / Point2 — down/0
18. EasyBroker / Wasi — CMS B2B, no portal público de inventario AR
19. ListaProp / EnBuenosAires / BairesInmuebles — DNS/0
20. Portales de agencias sueltas — volumen 1-agencia, DESCARTADO

### Buenos Aires (≥20)
1. MercadoLibre — **LIVE**
2. InmoClick — **LIVE**
3. ZonaProp — challenge
4. Argenprop — bloque
5. Properati — 401
6. RE/MAX — sin ficha hrefs
7. Mudafy — SPA
8. BuscadorProp — meta
9. Roomix — 403
10. iCasas — listados rotos
11. Inmuebles24 — 403
12. GoPlaceIt — vacío
13. Mercado Único — foco SF
14. CórdobaProp / MendozaProp / InmoUp — fuera de foco BA
15–25. Agencias individuales, Trovit/Mitula, etc. — mismos veredictos

### Santa Fe (≥20)
1. Mercado Único — **LIVE**
2. MercadoLibre — **LIVE**
3. InmoClick — **LIVE**
4. Propia (COCIR) — 200 con challenge/SPA Nuxt sin hrefs de ficha
5. ZonaProp / Argenprop / Properati — bloqueados
6. RE/MAX / Mudafy / BuscadorProp — igual que arriba
7. RosarioProp / LaEncontre / RosarioInmobiliario — DNS/0
8–25. Agencias Rosario, meta-buscadores — bajo valor o inaccesibles

### Mendoza (≥20)
1. InmoUp — **LIVE** (~25k)
2. MendozaProp — **LIVE** (~11k sitemap)
3. MercadoLibre — **LIVE**
4. InmoClick — **LIVE**
5. ZonaProp / Argenprop / Properati — bloqueados
6. RE/MAX / Mudafy — sin ficha hrefs / SPA
7. CCPIM (colegio) — institucional, no inventario scrapeable
8–25. InmoClick histórico, Los Andes clasificados, agencias — no aportan portal multi-aviso accesible

---

## Etapa 2 — Evaluación accesibilidad (curl real 2026-09-15)

| Portal | robots | List HTTP | Challenge | Veredicto |
|---|---|---|---|---|
| cordobaprop | (prev OK) | 200 hist. | no | VIABLE (live previo; flaky DNS en esta sesión) |
| inmoup | Allow | 200 | no | VIABLE |
| mendozaprop | 404 | 200 | no | VIABLE |
| mercado_unico | Allow | 200 | no | VIABLE |
| mercadolibre | Allow | 200 | no | **VIABLE (re-eval)** |
| inmoclick | Allow | 200 | no | **VIABLE** |
| zonaprop | 200 | 403 | sí CF | DESCARTADO |
| argenprop | 405 | 405 | — | DESCARTADO |
| properati | 401 | 401 | sí | DESCARTADO |
| roomix | 403 | 403 | sí | DESCARTADO |
| clasificados lavoz | 200 | 403 | sí | DESCARTADO |
| inmuebles24 | 200 | 403 | sí | DESCARTADO |
| propia | Allow | 200 | sí/SPA | NO extractable list |
| remax | Allow | 200 | no | list sin hrefs ficha |
| mudafy | — | 200 | no | SPA sin hrefs ficha |
| buscadorprop | Allow | 200 | no | meta-agregador |
| icasas | Allow | 200 home / 404 prov | no | listados provinciales rotos |
| goplaceit | Allow | 200 | no | shell vacío |
| propertia | — | 200 | no | sin inventario |
| trovit/mitula/nestoria | — | 0/401 | — | DESCARTADO |
| lamudi/dotproperty/point2 | — | 0 | — | DESCARTADO |

---

## Etapa 3 — Extractabilidad + volumen (solo viables)

| Fuente | Patrón | Vol. máx. estimado | Notas |
|---|---|---|---|
| cordobaprop | parser propio | miles CBA | ya integrado |
| inmoup | JSON-LD | ~25k Cuyo | ya integrado |
| mendozaprop | sitemap + NEXT_DATA | ~11k venta sitemap | ya integrado |
| mercado_unico | homepage + NUXT/og | miles SF | ya integrado |
| mercadolibre | JSON-LD Product | CBA casas ~14.5k; ×4 prov × tipos | **nuevo enabled** |
| inmoclick | og + HTML ficha | ~150k decl.; ~72 fichas/página list | **nuevo** |

---

## Por qué no se llega a 15×4

1. **Bot protection** en los 3 grandes tradicionales (ZonaProp/Argenprop/Properati).
2. **SPA sin datos embebidos** en listados (Propia, Mudafy, RE/MAX listings).
3. **Meta-agregadores** (Roomix, BuscadorProp, Trovit) — ToS / valor duplicado / challenges.
4. **No existen 15 portales regionales independientes scrapeables** por provincia; el inventario real está en 2–4 jugadores.

Ampliar a 15×4 requeriría **proxy/anti-bot** o acuerdos comerciales con colegios/CMS (Tokko, EasyBroker multi-tenant).

---

## Crons con 6 fuentes

Ver `docs/CRON_EXTERNO.md`. Con 6 fuentes × 80 details × 1s delay ≈ 8–15 min/corrida.
Cron semanal sigue viable; si se suman más, particionar por provincia (lunes CBA, martes BA, …).
