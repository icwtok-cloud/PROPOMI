# Progress Log — Propomi

Este archivo es el historial vivo del proyecto. Se agrega una entrada nueva
cada vez que se cierra y pushea una parte del trabajo. Entrada más reciente
arriba. No se borran entradas viejas.

Formato de cada entrada:

```
## [fecha] — [etapa del roadmap tocada]
- Qué se hizo
- Qué quedó pendiente / no se llegó a hacer
- Decisiones tomadas sobre la marcha (y si son reversibles)
- Archivos tocados
```

---

## 2026-09-13 — Etapa 0: setup del sistema de trabajo colaborativo

- Se leyó completo el documento maestro (`Propomi-Documento-Maestro.docx`)
  provisto por el dueño del producto y se copió sin cambios de contenido a
  `docs/PLAN_MAESTRO.md` dentro del repo, para que quede versionado junto
  al código en vez de vivir solo como un Word suelto.
- Se creó `CLAUDE.md` con las instrucciones de cómo debe operar cualquier
  sesión de IA que retome este repo.
- Se creó este archivo (`PROGRESS_LOG.md`) como historial vivo.
- **Decisión operativa (reversible):** por ahora no hay Claude Code
  conectado a este repo. El trabajo se hace en un chat normal de Claude.ai:
  el usuario pega el archivo puntual a tocar, Claude devuelve el reemplazo
  completo, el usuario aplica/testea/commitea/pushea localmente. Si en el
  futuro se conecta Claude Code, este flujo se reemplaza por trabajo directo
  sobre el repo clonado.
- **Próxima etapa a encarar (según roadmap, sección 10 del plan maestro):**
  Etapa 1 — Modelo de datos ampliado (`AgencyPhone`, verificación en dos
  niveles + Instagram/link, `Property.images` como lista, `Subscription` y
  `LeadCredit`, separar `freshness` en `detected_at`/`origin_published_at`).
  Todavía no se tocó ningún archivo de código.
- Archivos tocados: `CLAUDE.md` (nuevo), `PROGRESS_LOG.md` (nuevo),
  `docs/PLAN_MAESTRO.md` (nuevo).
