# PROGRESS_LOG — MAX_AGE_DAYS + origin_published_at

1. HEAD: `1e17a663030582f04b1b935eb558bba422fadbe0`.
2. Parte A: `parse_origin_date` en normalize.py; MAX_AGE_DAYS=90; filtro solo en create de upsert_payload.
3. Parte B: extracción best-effort de datePublished/similares en zonaprop, mercadolibre, argenprop, infocasas, bienesonline.
4. Unit-test parse_origin_date: ISO, dd/mm, vacío, None, basura → OK.
5. Diff: 135+/2− en 7 archivos, quirúrgico.
