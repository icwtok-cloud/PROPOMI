# PROPOMI — Encargo de construcción en una sola pasada

**Destinatario:** Grok (o cualquier IA con acceso al repo).
**Repo:** `https://github.com/icwtok-cloud/PROPOMI` — rama `main`.
**Fecha del encargo:** 2026-09-15.
**Modo de trabajo:** **una sola pasada.** Construí las 6 tareas de abajo
completas y entregá todo junto al final. No pidas confirmación entre
tareas, no entregues por partes, no preguntes qué hacer primero — el orden
ya está fijado abajo y las dependencias ya están resueltas.

> **Nota de contexto que te va a confundir si no la leés:** el archivo
> `CLAUDE.md` del repo dice explícitamente "trabajar en partes chicas,
> nunca una etapa completa en un solo tramo". Esa regla existe porque las
> sesiones de chat largas se cortaban antes de pushear. **Para este encargo
> queda suspendida** por decisión del dueño del producto. Si tu contexto no
> alcanza para las 6 tareas, decilo al principio y entregá hasta donde
> llegues con un corte limpio (repo compilando), en vez de entregar las 6 a
> medias.

---

## 0. Antes de escribir una línea de código: leé esto

En este orden, del repo clonado:

1. `PROGRESS_LOG.md` — **es la fuente de verdad del estado actual.**
2. `docs/PLAN_MAESTRO.md` — fuente de verdad de **reglas de negocio**
   (secc. 5) y **decisiones de producto** (secc. 6). **Su descripción del
   "estado actual" está desactualizada y es incorrecta** — dice que el
   crawler y las suscripciones no existen, y ambos existen. No te guíes por
   eso; la tarea 6 de este encargo es justamente arreglarlo.
3. `apps/api/app/main.py` (3508 líneas, 56 endpoints, 17 tablas).
4. `apps/api/app/crawler/` completo.

**Ambiente:** el dueño del producto **no tiene ambiente de test local** (ni
`pytest` ni `npm run build` corren en su máquina). La primera corrida real
es el deploy en Render (backend) / Vercel (frontend). Por eso vos tenés que
correr `pytest` en tu propio entorno antes de entregar, y decir
explícitamente qué corriste y qué no.

---

## 1. Reglas que no se rompen (si dudás, frená y preguntá)

Vienen de la sección 5 del plan maestro. **Cualquier entrega que rompa una
de estas se rechaza entera**, aunque el resto esté bien:

1. `buyer_name`, `buyer_phone`, `buyer_email` **nunca** viajan en ninguna
   respuesta de API salvo que `contact_revealed == true` para esa oferta
   puntual.
2. Ningún campo de texto libre nuevo se guarda sin pasar por
   `sanitize_free_text()`. Ni en el panel interno de admin.
3. La descripción scrapeada también se limpia (`strip_contact_leaks`), no
   solo lo que escribe un usuario dentro de Propomi.
4. El comprador nunca escribe texto libre en condiciones; el agente nunca
   responde con texto libre. Solo botones estructurados.
5. Identidad canónica del agente = teléfono normalizado E.164, no email.
6. El canal B2B agente↔agente es gratis siempre, y no puede usarse para
   reenviar un contacto ya capturado por el canal B2C.
7. El crawler nunca dispara contacto en frío al publicar. Solo cuando llega
   una oferta real (B2C) o una consulta B2B.
8. El crawler no entra detrás de login, no hardcodea credenciales, y no
   toca fuentes con `enabled=False` en `selectors.py`.

---

## 2. Las 6 tareas, en orden

### Tarea 1 — Borrar los endpoints de debug (10 minutos, hacela primero)

En `apps/api/app/main.py`, eliminar:

- `POST /admin/debug/create-test-agency` (~línea 3167)
- `GET /admin/debug/agency-by-id/{agency_id}` (~línea 3196)
- el modelo `DebugCreateAgencyIn` (~línea 3160)

Ambos tienen docstring "DEBUG TEMPORAL — borrar después de resolver el test
de Lemon Squeezy (tarea 5)". Esa tarea ya se resolvió. El problema concreto:
`create-test-agency` crea una `Agency` con `verification_status="VERIFIED"`
directo, salteando toda la cola de revisión manual de la Etapa 4.

**Criterio de aceptación:** `grep -rn "admin/debug" apps/` no devuelve
nada, y los 30 tests siguen pasando.

---

### Tarea 2 — Proceso periódico de antigüedad (plan maestro secc. 7)

**El problema:** `MAX_AGE_DAYS = 90` en `crawler/runner.py` es **solo filtro
de entrada**. Una propiedad indexada hace 55 días va a superar el límite
mientras sigue publicada en Propomi y nadie la vuelve a mirar nunca. El plan
maestro pide un proceso periódico que la oculte al cumplir el límite.

**Construir:**

1. Campo nuevo en `Property`: `hidden_at` (`DateTime`, nullable, default
   `None`). No borrar filas — ocultar. Si una propiedad reaparece en el
   portal de origen en una corrida posterior del crawler, el upsert debe
   poder resetear `hidden_at` a `None`.
2. Función `expire_stale_properties(db) -> dict` que setee `hidden_at` en
   toda `Property` con `hidden_at IS NULL` y antigüedad efectiva mayor a
   `MAX_AGE_DAYS`. **Antigüedad efectiva** = `origin_published_at` si
   existe, si no `detected_at`. Devuelve un reporte con cuántas ocultó.
3. `GET /properties` y `GET /properties/{id}` filtran `hidden_at IS NULL`
   por defecto. Agregar un query param `include_hidden=false` que solo
   surta efecto con `X-Admin-Key` válido — un agente no debe poder ver las
   ocultas de otros.
4. `POST /admin/properties/expire-stale`, protegido por `require_admin`,
   que corre `expire_stale_properties` y devuelve el reporte.
5. En `render.yaml`, agregar un `type: cron` con `schedule: "0 4 * * *"`
   (4 AM UTC = 1 AM Argentina, tráfico mínimo) que haga POST a ese
   endpoint. Si el plan de Render en uso no soporta cron jobs, **dejarlo
   escrito igual y comentado**, con una nota de una línea explicando la
   alternativa (llamada desde un scheduler externo tipo cron-job.org con la
   `X-Admin-Key` en header).

**Tests obligatorios** en un archivo nuevo `tests/test_property_expiry.py`:
propiedad de 100 días se oculta; de 30 días no; una con
`origin_published_at` viejo pero `detected_at` reciente **sí** se oculta
(la antigüedad del portal de origen manda); `GET /properties` no devuelve
las ocultas; con admin key e `include_hidden=true` sí.

---

### Tarea 3 — Habilitar ZonaProp (la "tarea 13" pendiente)

**Contexto:** hoy la única fuente con `enabled=True` es `cordobaprop`. El
plan maestro fija como zona piloto **Caballito, CABA**, que CordobaProp no
cubre. Argenprop, MercadoLibre y Properati devuelven **403 en el borde**
(CloudFront / bot protection / AWS ELB) — están fuera de alcance sin una
solución anti-bot dedicada, no las toques. **ZonaProp es el desbloqueo del
piloto** y su robots.txt ya fue confirmado el 2026-09-15.

**Reglas exactas del robots.txt de ZonaProp** (están documentadas en el
comentario de `selectors.py`, respetalas al pie de la letra):

- Permite fichas con patrón `/propiedades/*-ubicado-en-*`. El resto de ese
  patrón de URL está bloqueado.
- Paginación: **solo páginas 2 a 5** (tanto `*pagina-N.html` como
  `*pagina=N`). La página 1 es implícita. Nada más allá de la 5.
- Bloquea: `/develop/ /mails/ /errores/ /bloques/ /bumex/ /cms/ /panel/
  /ecommerce/ /static/ /publica-tu-propiedad/ /zp/ /tracking/`.
- Bloquea cualquier URL con query param `utm_*`, `n_src=`, `gad_source=`,
  `gclid=`, `fbclid=`, `duplicated=true`, `labs=`.

**Hacer:**

1. Revisar `crawler/queries.py::zonaprop_list_urls` y verificar que las URLs
   que genera caen dentro de lo permitido (páginas 1-5, sin query params
   prohibidos). Corregir si no.
2. Revisar `crawler/links.py` para ZonaProp: que solo extraiga URLs que
   matcheen `/propiedades/*-ubicado-en-*` y descarte el resto.
3. Validar `crawler/parsers/zonaprop.py` contra HTML real. El parser está
   escrito contra el **JSON embebido** en el HTML, no contra selectores CSS
   — si la estructura del JSON cambió, ajustala. **Guardá un fixture de
   HTML real** en `apps/api/tests/fixtures/zonaprop_detail.html` y escribí
   un test que parsee ese fixture, para que la próxima caída de selectores
   se detecte en CI y no en producción.
4. Apuntar `zonaprop_list_urls` a **Caballito, CABA**, solo venta.
5. Recién con lo anterior verde: `enabled=True` en `selectors.py`, y
   actualizar `robots_note` con la fecha de validación.

**Criterio de aceptación:** una corrida de `POST /admin/crawler/run?sources=zonaprop`
trae fichas reales de Caballito con `title`, `price`, `zone`, `surface`,
`rooms` e `images` poblados y **sin mojibake** (verificá que aparezca
"Caballito" y no "Caballito" corrupto — ver el bug de encoding ya
corregido en `_get()`). Y que `description` salga sin teléfonos ni emails
(regla no negociable #3).

---

### Tarea 4 — Paginación con estado en el crawler

**El problema:** `MAX_LIST_PAGES_PER_SOURCE = 3` y
`MAX_DETAILS_PER_SOURCE = 15` significan ~15 fichas por fuente por corrida,
y como no hay cursor persistido, **cada corrida reempieza desde la página 1
y vuelve a traer casi lo mismo.** Con eso no se llena una zona piloto nunca.

**Construir:**

1. Tabla nueva `CrawlCursor`: `source_id` (PK), `last_page`,
   `last_run_at`, `total_seen`.
2. `runner.discover_detail_urls` arranca desde `last_page + 1` en vez de
   siempre desde la primera, y persiste el avance al terminar.
3. Cuando el cursor llega al tope permitido por la fuente (para ZonaProp:
   página 5, por robots.txt), **reinicia a 1** — a esa altura las primeras
   páginas ya tienen avisos nuevos, y el upsert es idempotente.
4. Subir `MAX_DETAILS_PER_SOURCE` a 40 y mantener
   `REQUEST_DELAY_SECONDS = 1.0`. No lo subas más: son portales de terceros
   y el dyno de Render es chico. La cortesía no es opcional.
5. Cron diario en `render.yaml` para `POST /admin/crawler/run` (mismo
   criterio y misma nota que la tarea 2 si el plan no soporta cron).

**Tests:** el cursor avanza entre corridas; reinicia al llegar al tope; dos
corridas seguidas no duplican filas en `Property` (el upsert es
idempotente).

---

### Tarea 5 — Checklist de calidad (plan maestro secc. 11)

Antes de entregar, verificá y **reportá cada ítem explícitamente** con
resultado, no con un "listo":

- [ ] `pytest apps/api/tests/` → los **30 tests existentes siguen pasando**,
      más los nuevos que agregaste. Si algún test viejo falla, lo arreglás
      vos, no lo borrás ni lo marcás `skip`.
- [ ] `npm run build` en `apps/web` sin errores ni warnings de imports
      faltantes (si tocaste frontend; en este encargo casi todo es backend).
- [ ] Repasá las 8 reglas no negociables de la sección 1 de este documento,
      **una por una, por escrito**.
- [ ] `buyer_name`/`buyer_phone`/`buyer_email` siguen sin viajar salvo
      `contact_revealed=true`.
- [ ] Ningún campo de texto libre nuevo sin `sanitize_free_text()`.
- [ ] Entregá el **paquete completo**, nunca archivos sueltos — un import
      roto por un archivo faltante es el error más común y más evitable en
      este repo.
- [ ] Listá las **variables de entorno nuevas** y dónde cargarlas (Render
      para backend, Vercel para frontend).
- [ ] El modelo de datos cambia en las tareas 2 y 4 (`Property.hidden_at`,
      tabla `CrawlCursor`). **Explicá qué pasa con los datos que ya
      existen.** El repo usa migración incremental de columnas en
      `main.py` (agrega columnas nuevas comprobando antes si ya existen,
      sin borrar datos) — seguí ese patrón, no metas Alembic.

---

### Tarea 6 — Regenerar `docs/PLAN_MAESTRO.md`

El plan maestro contradice al código en al menos 6 puntos (están tabulados
en la primera entrada de `PROGRESS_LOG.md`). Reescribí las secciones **3
(estado real del código), 4 (modelo de datos), 7 (crawler), 8
(monetización) y 10 (roadmap)** para que reflejen el estado real después de
tus cambios.

**No toques las secciones 5 (reglas no negociables) ni 6 (decisiones de
producto)** — salvo un único ajuste puntual: la decisión **6.2.1** (login de
Google obligatorio para el comprador) **fue revertida** el 2026-09-14
(commit `7de1dff`): hoy el SMS verificado alcanza y Google quedó opcional,
porque el doble gate mataba la conversión al final del wizard. Documentá
ese cambio con su motivo, no lo borres en silencio.

Agregá al final una entrada tuya en `PROGRESS_LOG.md` siguiendo el formato
del archivo (más nuevo arriba, con secciones de qué se hizo / qué se
validó / qué quedó pendiente / archivos tocados).

---

## 3. Formato de entrega

- Un solo paquete con **todos** los archivos tocados completos (no diffs
  parciales, no fragmentos).
- Si son varios archivos, un `.zip`.
- Nombres de descarga con sufijo de versión único (`main_v7.py`,
  `PROGRESS_LOG_v13.md`) — el dueño del producto trabaja en Windows y los
  nombres repetidos generan `(1)`, `(2)` automáticos.
- Mensaje de commit sugerido, en una línea, sin emojis.
- Un resumen al final con: qué construiste, qué corriste de verdad vs. qué
  no pudiste correr, qué variables de entorno nuevas hay que cargar, y qué
  quedó pendiente.

## 4. Lo único que sí tenés que preguntar

Todo lo demás decidilo vos con el default más razonable y marcalo como
reversible. La única pregunta que amerita frenar es si **descubrís que
ZonaProp tampoco es viable** (por ejemplo, que el HTML real esté detrás de
un challenge de Cloudflare que el robots.txt no anticipaba). En ese caso no
sigas con la tarea 3: entregá las tareas 1, 2, 4, 5 y 6, y avisá — porque
eso obliga a una decisión de producto que no te corresponde (mover la zona
piloto de Caballito a Córdoba, o invertir en una solución anti-bot).
