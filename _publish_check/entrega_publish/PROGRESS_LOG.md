# PROGRESS_LOG — Publicar nueva + GeoCity

1. HEAD confirmado: `1e17a663030582f04b1b935eb558bba422fadbe0`.
2. Modelo GeoCity + UniqueConstraint + create_all.
3. GET /geo/catalog merge estáticas + DB; POST /geo/cities con dedup exacto/fuzzy + rate-limit 20/día.
4. api.ts: addGeoCity.
5. AgentDashboard: form en secciones con selects; flujo "+ Otra ciudad" con confirmación fuzzy.
6. globals.css: estilos publish-* (reemplazo de chips).
7. Unit-test dedup: Libertades/Libertadez/Córdoba OK.
