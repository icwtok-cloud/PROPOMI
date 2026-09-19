# Expansión crawler 2026-09-19 — fuera de portales clásicos + MX

## Objetivo
Ampliar inventario hacia ~150k fichas acumuladas (corridas cron + dedup), sumando:
- Portales alternativos AR scrapeables
- Segmento **pozo / desarrollos**
- Segmento **campos / chacras**
- **MercadoLibre México**
- Tipos de propiedad nuevos en UI (`Campo`, `Chacra`)

## Fuentes nuevas (`enabled=True`)

| Source id | País | Segmento | Patrón | Est. por corrida* |
|-----------|------|----------|--------|-------------------|
| `argencasas` | AR | Urbano GBA/AR | `/propiedad-*` + JSON-LD | ~30–150 |
| `departamentosenpozo` | AR | Pozo CABA/GBA | `/desarrollos-inmobiliarios/{slug}/` | hasta ~200 (cap runner) |
| `bullano` | AR | Campos/chacras | `/campos/ficha/{slug}-{id}.html` | ~50–150 |
| `mercadolibre_mx` | MX | Urbano | poly-card + JSON-LD Product (MLM-) | ~200 (cap) |

\*Por corrida limitada por `MAX_DETAILS_PER_SOURCE` en `runner.py` (200). Inventario total crece con el cron.

## Fuentes LIVE totales: **13**
Previas (9): cordobaprop, mendozaprop, mercado_unico, mercadolibre, inmoup, inmoclick, bienesonline, infocasas_py, infocasas_uy.  
Nuevas (4): argencasas, departamentosenpozo, bullano, mercadolibre_mx.

## ML AR ampliado
`mercadolibre_list_urls` ahora itera **5 tipos** × 24 provincias = **120 listados**:
`casas`, `departamentos`, `ph`, `terrenos`, `campos`.

## UI — pills de tipo
`PROPERTY_TYPES` / `PROP_TYPES` incluyen **Campo** y **Chacra**.  
Filtro “En Pozo” acepta `underConstruction` **o** `type === 'En Pozo'`.

## No viable (reconfirmado)
ZonaProp/Argenprop/Properati/Gallito (CF), RE/MAX (SPA), Encuentra24 (SPA), iCasas listados sin fichas.

## Archivos
- Parsers: `argencasas.py`, `departamentosenpozo.py`, `bullano.py`
- `queries.py`, `links.py`, `selectors.py`, `parsers/__init__.py`, `normalize.py`
- `mercadolibre.py` (tipos + MLM id)
- FE: `page.tsx`, `AgentDashboard.tsx`
- Tests/fixtures: `test_argencasas_parser.py` + HTML reales

## Próximas tandas sugeridas
1. Subir `MAX_DETAILS_PER_SOURCE` / páginas de listado cuando el cron demuestre estabilidad.
2. Parser genérico Tokko (webs de agencias).
3. Más desarrolladoras individuales si departamentosenpozo deja huecos.
4. ML UY vía `/c/inmuebles` (re-eval).
