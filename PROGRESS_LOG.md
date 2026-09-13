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

## 2026-09-13 — Etapa 1 v2: modelo de datos ampliado (apps/api/app/main.py)

- **Archivo pusheado:** `apps/api/app/main.py` → versión **v2** (la anterior,
  la que ya estaba en el repo, queda como v1 de referencia en este log).
- **Agregado sobre `Agency`:** `verification_status` (PENDING/VERIFIED/
  REJECTED, default PENDING), `instagram`, `website_link`,
  `verification_priority`, `verification_reviewed_at`,
  `verification_notes`, `free_leads_remaining`. El booleano `verified`
  viejo se deja como DEPRECATED (no se borra, para no romper nada que ya
  lo lea) pero deja de ser la fuente de verdad.
- **Agregado sobre `Property`:** `images` (lista JSON, hasta
  `MAX_PROPERTY_IMAGES = 5`) y `origin_published_at` (antigüedad declarada
  por el portal de origen, separada de `detected_at` que ya existía).
  `freshness` e `image` (singular) quedan DEPRECATED pero no se borran.
- **Migración de datos:** `migrate_legacy_property_images()` corre una vez
  al iniciar el proceso y completa `images=[image]` en toda fila vieja que
  todavía tenga `images` vacío — se eligió migrar el dato viejo, no
  arrancar de cero (doc 06 / 04.2).
- **Conectado `reveal_contact`:**
  - Ahora bloquea con 403 si `agency.verification_status != "VERIFIED"`
    (antes no existía ningún chequeo de verificación acá — un agente recién
    creado ya podía revelar contacto, lo cual contradecía la decisión 6.2.2
    del plan maestro).
  - Consume `free_leads_remaining` antes que el cupo de suscripción o el
    pay-per-lead, para los primeros 10 reveals gratis al verificarse (doc
    06.2.3 / 08). Es un contador separado, no se pisa con el cupo de plan.
- **`PATCH /agencies/{id}`** ahora acepta `instagram` y `website_link` para
  que la agencia pueda cargarlos desde "Mi cuenta" — la cola de revisión
  manual en sí (aprobar/rechazar) queda para la Etapa 4, no se construyó
  todavía.
- **Bug encontrado y corregido (no estaba documentado en la sección 12 del
  plan maestro):** la función `offer_action` (aceptar / rechazar /
  negociar una oferta) no tenía decorador `@app.post(...)` — el endpoint
  nunca estuvo expuesto en la API, solo funcionaban `/counter` y
  `/reveal`. Se agregó `@app.post("/offers/{offer_id}/{action}")`.
- **Pendiente / no se tocó en esta etapa:**
  - Panel interno de revisión manual (Etapa 4).
  - `Subscription` como tabla separada (se mantiene el enfoque actual de
    campos inline en `Agency` — funciona igual, se puede migrar a tabla
    propia más adelante si hace falta reportar historial de ciclos).
  - No se pudo correr `pytest` ni levantar el servidor en este entorno
    (sin acceso a red/pip) — **el usuario tiene que correr el checklist de
    la sección 11 del plan maestro localmente** (`pytest` +
    `npm run build` si tocó frontend) antes de pushear, y avisar acá si
    algo falla.
- Archivos tocados: `apps/api/app/main.py` (reemplazo completo → v2),
  `CLAUDE.md` (v2 — se agregaron las reglas fijas de entrega: PowerShell
  exacto, zip si son varios archivos, versionado creciente por archivo).

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
