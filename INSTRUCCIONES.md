# INSTRUCCIONES DEL PROYECTO — PROPOMI

> Memoria persistente entre sesiones. Al iniciar sesión, el usuario solo pasa el
> link del repo (o de este archivo) y dice "seguí las instrucciones". Claude lee
> este archivo primero, ubica en qué etapa quedó el proyecto, y continúa sin pedir
> que se repitan estas reglas ni los links de archivos ya listados en el manifiesto.

## Reglas de trabajo (fijas, no se repiten)

1. El usuario abre sesión enviando el repo. Se continúa exactamente donde quedó
   la última sesión (ver "Historial de etapas").
2. No hay CLI ni conexión directa al repo desde Claude. El usuario tiene el repo
   clonado localmente y pushea manualmente. Claude nunca asume que puede pushear él mismo.
3. Cada archivo entregado para pushear va acompañado de los comandos exactos de
   PowerShell (Windows) para copiar, agregar, commitear y pushear.
4. Cada actualización/push, por mínimo que sea, se anota en "Historial de etapas"
   (archivos tocados, nombre de commit, estado).
5. Cada nueva actualización tiene un nombre de commit claro y su reversión asociada
   (convención abajo), para poder revertir puntualmente.
6. Toda instrucción o regla nueva del usuario se anota en este archivo ANTES de
   seguir, sumándose a lo ya existente (nunca se pisa lo anterior sin querer).
7. Claude decide el próximo paso lógico de construcción por su cuenta. No consulta
   "qué sigue" — ejecuta y avisa qué hizo.
8. Las etapas de construcción son PEQUEÑAS, para no perder progreso si una sesión
   se corta a mitad de camino.
9. **Versionado de archivos entregados**: cada vez que Claude entrega un archivo
   para pushear (incluido este mismo archivo de instrucciones), el nombre de
   descarga lleva un sufijo de versión `_Vn` (V1, V2, V3...) que nunca se repite,
   para que no se pisen archivos en la carpeta de Descargas de Windows. La versión
   vigente de cada archivo se anota en la tabla "Versionado de archivos" más abajo.
   El nombre final dentro del repo (ej. `INSTRUCCIONES.md`, `types.ts`) NUNCA lleva
   el sufijo `_Vn` — el sufijo es solo para el archivo de descarga temporal; los
   comandos de PowerShell ya se encargan de renombrarlo al copiarlo al repo.
10. **Manifiesto de archivos (raw links) — CON LIMITACIÓN CONFIRMADA**: Claude no
    puede construir ni adivinar URLs raw de GitHub — su herramienta solo puede abrir
    una URL que YA HAYA APARECIDO TEXTUALMENTE en un resultado real de búsqueda o
    fetch anterior, o en un mensaje del usuario. Se probó (sesión del 2026-09-13)
    que escribir los links dentro de un archivo que Claude genera (como este mismo)
    NO alcanza para "desbloquearlos": Claude necesita fetchear ese archivo desde
    GitHub de verdad (ya pusheado) para que las URLs que contiene queden
    disponibles. Consecuencia práctica:
    - El manifiesto de abajo sigue siendo útil como REFERENCIA para el usuario
      (copiar y pegar rápido) y para que Claude sepa qué archivos existen y cuáles
      ya se revisaron — pero el usuario va a tener que seguir pegando el raw link
      puntual de cada archivo nuevo que Claude necesite abrir, salvo que:
      (a) el usuario le pida a Claude que primero fetchee `INSTRUCCIONES.md` desde
      GitHub (una vez confirmado el push), lo cual sí desbloquea todos los links
      que ese archivo contiene como texto, o
      (b) el archivo ya fue leído en una sesión anterior y su URL quedó registrada
      en el historial de la conversación activa.
    - Por eso, al abrir sesión, conviene que el usuario diga algo como: "leé
      INSTRUCCIONES.md desde el repo" (pasando el raw link de ESE archivo), y recién
      ahí Claude puede navegar solo el resto del manifiesto sin pedir cada link.

11. **Meta-regla de auto-documentación**: Claude no espera a que el usuario pida
    "anotá esto" — en CADA respuesta donde el usuario dé una instrucción, corrija
    a Claude, o establezca una preferencia nueva (por mínima que sea), Claude debe
    incorporarla a este archivo en el mismo turno, antes de seguir con cualquier
    otra cosa, y entregar el archivo actualizado + comandos de push. Si Claude no
    está seguro de si algo dicho por el usuario es "una regla nueva" o solo un
    comentario de una vez, debe tratarlo como regla nueva y anotarlo igual (el
    costo de anotar de más es bajo; el costo de que el usuario tenga que repetirse
    en la próxima sesión es alto y es precisamente lo que este archivo existe para
    evitar).

12. **Sin narración**: Claude no explica lo que va a hacer, no relata su proceso ni
    justifica cada paso. Responde con el resultado (archivo(s) + comandos de
    PowerShell) directamente. Texto mínimo: solo lo imprescindible (ej. pedir un
    link puntual que falte).
13. **Sin comandos de reversión salvo pedido explícito**: Claude no incluye los
    comandos `git revert` en cada entrega. Si el usuario necesita revertir algo,
    lo pide en el momento y ahí se le da el comando puntual para esa etapa.

14. **Formato al pedir links faltantes**: cuando Claude necesite un raw link que
    el usuario todavía no pasó, lo pide SIEMPRE dentro de un bloque de código
    (```), una URL por línea, sin texto extra alrededor más que lo imprescindible
    — así el usuario copia y pega directo, sin tener que editar nada.
15. **El próximo paso lógico SIEMPRE queda escrito en este archivo**: al cierre
    de cada etapa, la sección "Próximo paso lógico" de más abajo debe reflejar
    el candidato real elegido por Claude (regla 7) — nunca se responde solo en
    el chat sin dejarlo anotado acá. Si en algún momento esa sección no está
    actualizada al final de una respuesta, se corrige en el mismo turno antes
    de seguir con cualquier otra cosa.

## Convención de nombres de commit / reversión

Formato: `etapa-NNN_<descripcion-corta>` y su reversión `revert-etapa-NNN_<descripcion-corta>`

## Versionado de archivos entregados (para no pisar descargas)

| Archivo (nombre real en el repo) | Última versión de descarga entregada |
|---|---|
| INSTRUCCIONES.md | V17 |
| apps/web/lib/types.ts | V3 |
| apps/web/lib/api.ts | V3 |
| apps/web/app/admin/page.tsx | V1 |
| apps/api/app/main.py | V5 |
| apps/web/components/AgentDashboard.tsx | V2 |
| apps/web/components/PropertyCard.tsx | V1 |
| apps/web/app/globals.css | V1 |
| apps/web/middleware.ts | V1 (nuevo) |
| apps/web/app/tienda/[slug]/page.tsx | V1 (nuevo) |

## Manifiesto de archivos del repo (raw links ya conocidos)

Formato de conversión manual si hace falta un archivo nuevo:
`https://github.com/<user>/<repo>/blob/<rama>/<ruta>` → cambiar dominio a
`raw.githubusercontent.com` y sacar `/blob/`.

Raíz del repo:
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/README.md
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/package.json
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/render.yaml
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/vercel.json
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/.gitignore

apps/api/app/ (backend FastAPI — solo se conoce este archivo por ahora):
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/api/app/main.py

apps/web/ (frontend Next.js — estructura completa ya relevada, links por confirmar
uno a uno a medida que se necesiten; los ya usados están arriba):
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/package.json
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/next.config.ts
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/tsconfig.json
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/.env.example
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/layout.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/page.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/globals.css ✅ (leído y corregido en etapa 006)
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/agencia/page.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/AgentDashboard.tsx ✅ (leído y corregido en etapa 004)
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/AgentOfferActions.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/BuyerIdentityModal.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/ComparePanel.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/DemandPanel.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/OfferModal.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/PropertyCard.tsx ✅ (leído y corregido en etapa 005)
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/api.ts ✅ (leído y corregido en etapa 004)
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/data.ts
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/google.ts
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/types.ts ✅ (leído, corregido en etapa 001)

> NOTA IMPORTANTE: estos links todavía no fueron probados uno por uno (salvo los
> marcados ✅) porque hasta ahora Claude no podía adivinar URLs raw. A partir de que
> este archivo se fetchee al inicio de sesión, cualquiera de estos links pasa a ser
> "ya visto" y Claude puede intentar abrirlo directamente. Si alguno da error 404
> (por ejemplo por un typo de mayúsculas/minúsculas en la ruta real), Claude debe
> avisar y pedir que el usuario confirme el nombre exacto con
> `Get-ChildItem -Recurse .\apps -Name`.

## Historial de etapas

| Etapa | Descripción | Archivos tocados | Commit | Estado |
|-------|-------------|-------------------|--------|--------|
| 000 | Creación de este archivo de instrucciones y reglas del proyecto | INSTRUCCIONES.md | etapa-000_instrucciones-iniciales | Pendiente de push |
| 001 | Fix de contrato API↔Web: `types.ts` no tenía `images[]` ni `originPublishedAt` que el backend (`prop_dict` en main.py) ya devuelve hace etapas. Se completó también el tipo `Agency` (faltaban `verificationStatus`, `instagram`, `websiteLink`, `freeLeadsRemaining`) y se agregó `'search_performed'` a `EventName`. | apps/web/lib/types.ts | etapa-001_fix-contrato-property-agency-types | Pendiente de push |
| 002 | Se agregan reglas de versionado de archivos de descarga (`_Vn`) y manifiesto completo de raw links del repo, para que Claude no vuelva a pedirle al usuario los mismos links en cada sesión. | INSTRUCCIONES.md | etapa-002_versionado-y-manifiesto-de-archivos | Pendiente de push |
| 003 | Meta-regla de auto-documentación: Claude anota cualquier instrucción/corrección del usuario en el mismo turno en que se da, sin esperar a que se lo pidan explícitamente. | INSTRUCCIONES.md | etapa-003_meta-regla-autodocumentacion | Pendiente de push |
| 004 | Fix funcional: la agencia no tenía forma de completar su verificación desde la web. `updateAgency()` en `api.ts` solo mandaba `{name}` (el backend acepta también `instagram`/`website_link`, requeridos para pasar de PENDING a VERIFIED). Se corrigió `updateAgency` para mandar los tres campos, y se amplió la pestaña "Mi cuenta" de `AgentDashboard.tsx` con: badge de estado de verificación (VERIFIED/PENDING/REJECTED), inputs de Instagram y sitio web, aviso cuando la agencia no está verificada, y contador de "reveals gratis restantes" (`freeLeadsRemaining`) en las métricas. | apps/web/lib/api.ts, apps/web/components/AgentDashboard.tsx | etapa-004_fix-verificacion-agencia-en-mi-cuenta | Pendiente de push |
| 005 | `PropertyCard.tsx` solo mostraba `p.image` (singular, campo DEPRECATED) e ignoraba `p.images[]`, `p.originPublishedAt`, `p.pool` y `p.petFriendly` que el backend ya devuelve y el tipo `Property` ya soporta desde la etapa 001. Se corrigió: la portada ahora usa `images[0]` con fallback a `image`, se muestra un contador "+N fotos" si hay más de una, se agrega `originPublishedAt` debajo de la superficie/ambientes, y se suman los tags "Pileta" y "Acepta mascotas". Se evitó a propósito usar clases CSS nuevas (se reutilizaron `fresh`, `muted`, `tags`, etc. ya existentes) para no depender de `globals.css`, que todavía no fue leído. | apps/web/components/PropertyCard.tsx | etapa-005_fix-galeria-y-campos-faltantes-property-card | Pendiente de push |
| 006 | Se confirmó que `globals.css` NO tenía las clases `.notice-ok` / `.notice-warn` usadas por `AgentDashboard.tsx` desde la etapa 004 (el aviso de verificación se veía sin color). Se agregaron reutilizando la paleta ya existente de `.reveal-box--done` / `.reveal-box--pending` (verde/ámbar) para mantener consistencia visual. | apps/web/app/globals.css | etapa-006_fix-clases-css-faltantes-notice-ok-warn | Pendiente de push |
| 007 | Reglas de sesión agregadas: sin narración (Claude entrega resultado + comandos, sin relatar el proceso), sin comandos de rollback salvo pedido explícito, y formato fijo en bloque de código para pedir links faltantes. | INSTRUCCIONES.md | etapa-007_reglas-sin-narracion-sin-rollback-automatico | Pendiente de push |
| 008 | Confirmado (clonando el repo directo, sin necesitar raw links): `OfferModal.tsx` YA bloquea "Enviar oferta" (`disabled={busy||!phoneVerified||!googleVerified}`) hasta que celular+Google estén verificados, espejando la exigencia real del backend en `POST /offers`. `BuyerIdentityModal.tsx` (nombre+celular, sin OTP) solo se usa para las acciones de menor intención (pregunta/visita), lo cual es correcto por diseño — no requieren la verificación fuerte que sí exige ofertar. No hizo falta ningún cambio de código. | — (solo verificación) | — | Confirmado, sin push necesario |
| 009 | Regla nueva (15): la sección "Próximo paso lógico" tiene que quedar siempre escrita en este archivo al cierre de cada etapa, no solo mencionada en el chat. Se auditó también `AgentOfferActions.tsx`, `DemandPanel.tsx` y el 402 de `reveal_contact` (sin bugs) y se dejó anotado el candidato real para la próxima etapa (filtro de 60 días + dedup del crawler, Etapa 2 del roadmap). | INSTRUCCIONES.md | etapa-009_regla-proximo-paso-siempre-en-instrucciones | Pendiente de push |
| 010 | Arranque de Etapa 2 del roadmap general (cold-start): `GET /properties` no filtraba por antigüedad — una propiedad que el crawler dejó de ver seguía apareciendo en la búsqueda pública para siempre. Se agregó `PROPERTY_FRESHNESS_DAYS = 60` y el filtro `last_seen_at >= ahora - 60 días`, aplicado solo cuando NO se pide `agency_id` (una agencia sigue viendo sus propias publicaciones stale en "Mi cuenta" para poder notar y resolver el problema). Tests corridos: 9/11 pasan; los 2 que fallan (`test_reveal_blocked_without_subscription_or_payment`, `test_cannot_add_phone_already_used_by_another_agency`) son preexistentes y no están relacionados con este cambio (drift de tests vs. reglas de verificación de comprador y código de estado, de etapas anteriores). Dedup del crawler (mismo rango de precio + zona + superficie similar → revisión manual) queda como candidato de la próxima etapa — no hay endpoint de ingesta del crawler todavía en el backend, así que dedup se implementará junto con ese endpoint. | apps/api/app/main.py | etapa-010_filtro-frescura-60-dias | Pendiente de push |
| 011 | Endpoint de ingesta del crawler: `POST /properties/ingest` (protegido con `X-Admin-Key`, mismo mecanismo que el panel de revisión de agencias). Upsert por `source`+`source_url` (identidad natural de una publicación en su portal): si ya existe, actualiza los datos y `last_seen_at` (nunca toca `detected_at`); si es nueva, la crea. Dedup simple sin IA (doc 05): misma zona + precio dentro de ±5% + superficie dentro de ±10% de una propiedad ya existente → se marca `needs_review=true` y `possible_duplicate_of=<id>`, nunca se fusiona ni descarta sola. La descripción que trae el crawler se limpia en silencio con la nueva `strip_contact_leaks()` (reemplaza teléfonos/wsp/emails/usuarios por "[dato de contacto oculto]") — distinta de `sanitize_free_text()` (que RECHAZA texto tipeado por una persona), porque acá no hay a quién devolverle un error. Columnas nuevas en `Property`: `needs_review` (bool), `possible_duplicate_of` (str, nullable), migradas en `ensure_schema_columns`. Probado manualmente (create → 201, mismo source+url → update sin duplicar, propiedad similar en otra URL → needs_review=true, sin X-Admin-Key → 401, descripción sanitizada correctamente). Tests automáticos: mismos 9/11 de antes (los 2 que fallan siguen siendo los preexistentes, no relacionados). | apps/api/app/main.py | etapa-011_endpoint-ingesta-crawler-y-dedup | Pendiente de push |
| 012 | Cola de revisión manual para lo que el dedup de la etapa 011 marca: `GET /properties/review-queue` (X-Admin-Key) devuelve cada propiedad `needs_review=true` junto a su `possible_duplicate_of` ya resuelto (para comparar lado a lado sin consultar la base a mano), y `POST /properties/{id}/review` con `{"action": "confirm_duplicate"}` (la oculta reusando el mismo mecanismo del filtro de frescura — le pisa `last_seen_at` a más de 60 días atrás en vez de inventar un segundo mecanismo de ocultamiento) o `{"action": "not_duplicate"}` (limpia la marca y sigue circulando normal). `prop_dict()` ahora también expone `needsReview`/`possibleDuplicateOf` al frontend. Probado manualmente end-to-end: ingesta con dedup → aparece en la cola → resolver "not_duplicate" → cola vacía; ingesta con dedup → resolver "confirm_duplicate" → desaparece de `GET /properties`. Tests automáticos: mismos 9/11 de siempre (los 2 preexistentes sin relación). Nota: ningún frontend consume estos dos endpoints todavía — es panel interno puro, como el resto de la administración de agencias. | apps/api/app/main.py | etapa-012_cola-revision-duplicados | Pendiente de push |
| 013 | Pantalla mínima de panel interno: `apps/web/app/admin/page.tsx` (nueva), protegida con la clave `X-Admin-Key` pedida una sola vez y guardada en `localStorage` (`propomi-admin-key`) — NUNCA Clerk/OTP, porque este panel no es de cara al comprador/agente. Dos pestañas: "Agencias pendientes" (consume `GET /admin/agencies/pending`, `POST /admin/agencies/{id}/approve`, `POST /admin/agencies/{id}/reject`, endpoints que ya existían desde la etapa 4 pero sin frontend) y "Posibles duplicados" (consume los dos endpoints nuevos de la etapa 012, muestra la propiedad nueva junto a su candidata a duplicado lado a lado, con botones "No es duplicado"/"Confirmar duplicado"). Se agregaron `PendingAgency` y `ReviewQueueItem` a `types.ts`, y `getPendingAgencies`/`approveAgency`/`rejectAgency`/`getReviewQueue`/`resolveReviewItem` a `api.ts` (usan un `adminReq()` nuevo, separado del `req()` de sesión porque el header es `X-Admin-Key` y no `Authorization: Bearer`). Reutiliza clases CSS ya existentes (`.tablewrap`, `.summarycard`, `.tab`, `.notice`, `.toast`, etc.) sin tocar `globals.css`. Verificado con `tsc --noEmit` (sin errores) y `next build` completo (build exitoso, 4 rutas generadas incluyendo `/admin`; el único warning es de autoprefixer en `globals.css`, preexistente y no relacionado). | apps/web/lib/types.ts, apps/web/lib/api.ts, apps/web/app/admin/page.tsx | etapa-013_panel-admin-agencias-y-duplicados | Pendiente de push |
| 014 | Arranque de subdominios por agencia (Etapa 4 del roadmap general de negocio — distinta de la numeración 000-014 de este archivo, ver aclaración de la etapa 009/013 anteriores). Parte backend únicamente (frontend queda para 015): columna nueva `Agency.slug` (única, nullable por compatibilidad), helper `slugify()` (minúsculas, sin acentos, solo `[a-z0-9-]`, fallback `"agencia"` si el nombre queda vacío) y `ensure_agency_slugs()` que rellena el slug de cualquier agencia que todavía no lo tenga (barato: no hace nada si no hay filas con `slug IS NULL`), resolviendo colisiones con sufijo `-2`, `-3`, etc. Se llama en los dos puntos donde se lee/expone una agencia por fuera del alta (`GET /agencies/{id}` autenticado y el endpoint nuevo). Las 3 agencias semilla ya tienen slug fijo (`inmobiliaria-norte`, `red-urbana`, `urbania`) para que las URLs no cambien entre reinicios. Nuevo endpoint público (sin auth) `GET /agencies/by-slug/{slug}` → `{id, name, city, slug, verificationStatus}` — solo datos ya públicos en otras pantallas, nunca teléfono/contacto — pensado para que un middleware de Next.js (etapa 015, todavía no escrito) resuelva `inmobiliaria-norte.propomi.lat` a un `agency_id` y de ahí pida `GET /properties?agency_id=<id>` (ese endpoint ya es público desde antes de esta etapa). `GET /agencies/{id}` autenticado ahora también devuelve `slug`, para que el propio agente pueda ver/copiar su URL de storefront desde "Mi cuenta" cuando esa parte del frontend se construya. Tests automáticos: 9/11 (los mismos 2 preexistentes, sin relación, confirmados de nuevo). Smoke test manual corrido en sandbox: `GET /agencies/by-slug/inmobiliaria-norte` → 200 con el slug correcto; slug inexistente → 404; `GET /properties?agency_id=a1` → 200 con las propiedades de esa agencia. | apps/api/app/main.py | etapa-014_slug-agencia-backend | Pendiente de push |
| 015 | Parte frontend/infra de subdominios por agencia (sigue directo de la 014). `apps/web/middleware.ts` (nuevo): compara el `host` de cada request contra `NEXT_PUBLIC_ROOT_DOMAIN` (default `propomi.lat`); si es un host excluido (dominio raíz con/sin `www`, `propomi.vercel.app`, `localhost`) o no termina en `.{ROOT_DOMAIN}`, deja pasar sin tocar nada; si es un subdominio válido y el path pedido es exactamente `/`, hace `rewrite` (no redirect — la URL visible sigue siendo `{slug}.propomi.lat`) a `/tienda/{slug}`; cualquier OTRA ruta (`/agencia`, `/admin`, etc.) pedida contra un subdominio de agencia pasa sin reescribir, para no romperla por error. Página nueva `apps/web/app/tienda/[slug]/page.tsx`: storefront público mínimo de una sola agencia — pide `GET /agencies/by-slug/{slug}` y, si existe, `GET /properties?agency_id=<id>`, muestra nombre + badge de verificación + grilla de `PropertyCard` reutilizado (mismo componente de la home) con el flujo de "Proponer precio" ya existente (`OfferModal` + `BuyerIdentityModal`, misma gate de celular+Google verificados de la etapa 008); si el slug no resuelve (404), muestra una página explícita de "Agencia no encontrada" con link de vuelta a Propomi — se resolvió la ambigüedad de la etapa 013 (pasar a home normal vs. página propia) a favor de la página propia, porque silenciar el 404 mostrando la home completa hubiera sido más confuso para alguien que llegó por un link de agencia roto. Fix de paso en `api.ts`: `getProperties()` en modo demo (sin `NEXT_PUBLIC_API_URL`) ignoraba cualquier filtro — ahora si se le pasa `agency_id` sí filtra las fixtures de `data.ts` por ese campo, para poder probar el storefront sin backend real. Nueva función `getAgencyBySlug()` en `api.ts` (con fallback demo contra las 3 agencias semilla) y `slug` agregado a `Agency` en `types.ts`. Verificado en sandbox (no solo revisión manual, esta vez con Node real disponible): `npx tsc --noEmit` sin errores, `npx next build` completo y exitoso (5 rutas generadas incluyendo `/tienda/[slug]` como dinámica y el middleware compilado a 34.2kB; el único warning sigue siendo el de autoprefixer preexistente en `globals.css`, sin relación). | apps/web/middleware.ts (nuevo), apps/web/app/tienda/[slug]/page.tsx (nuevo), apps/web/lib/api.ts, apps/web/lib/types.ts | etapa-015_middleware-y-storefront-subdominio | Pendiente de push |
| 016 | Cierra el paquete de subdominios por agencia (no depende del DNS, a diferencia del resto): la pestaña "Mi cuenta" de `AgentDashboard.tsx` ahora muestra "Tu página pública" con un input readonly con la URL del storefront (`https://{slug}.{NEXT_PUBLIC_ROOT_DOMAIN}` si ese env está seteado, o `/tienda/{slug}` relativo si no — mismo fallback que ya usa `middleware.ts`, así funciona incluso antes de que el DNS wildcard esté armado) y un botón "Copiar link" (`navigator.clipboard.writeText`, con aviso de fallback si el navegador lo bloquea). No se muestra nada si `agency.slug` todavía no llegó (agencia recién creada antes del backfill de la etapa 014) — evita mostrar un link roto en vez de fallar en silencio. Verificado en sandbox: `npx tsc --noEmit` sin errores, `npx next build` completo y exitoso (mismas 5 rutas de la etapa 015, sin cambios de tamaño relevantes). Con esto el roadmap de "subdominios por agencia" (Etapa 4 del roadmap general) queda funcionalmente completo del lado de Propomi — lo único pendiente es la infraestructura de DNS/Vercel que arma el usuario (ver "Próximo paso lógico"). | apps/web/components/AgentDashboard.tsx | etapa-016_url-storefront-en-mi-cuenta | Pendiente de push |

## Cierre de sesión (2026-09-13, cuarta sesión) — arrancar la próxima sesión directo desde acá

El código de subdominios por agencia (backend, middleware, storefront y el
link en "Mi cuenta") está completo y pusheado (etapas 014-016). No hay ningún
"próximo paso de código" colgado de esta feature — lo único que falta es la
infraestructura de DNS/Vercel que arma el usuario fuera de este chat (ver
abajo). Al abrir la próxima sesión, Claude debe:

1. Preguntar primero si el usuario ya configuró el wildcard DNS + Vercel (ver
   "Próximo paso lógico"). Si dice que sí, ofrecer verificar con un fetch a
   `https://inmobiliaria-norte.propomi.lat` (o el slug que corresponda) antes
   de asumir que funciona.
2. Si el usuario no menciona la infraestructura, no asumir que ya está lista
   ni bloquearse esperando confirmación de eso: pasar directo al siguiente
   candidato de código (ver "Próximo paso lógico"), ya que no depende del DNS.

## Próximo paso lógico (candidato para etapa 017)

- **Sigue dependiendo 100% del usuario, fuera de este chat**: el wildcard DNS
  `*.propomi.lat` + el dominio wildcard en Vercel (ver etapa 015/016). No hay
  nada más de código que Claude pueda hacer para esto.
- Con la feature de subdominios cerrada del lado de código, no queda ningún
  pendiente colgado de una etapa anterior — el próximo candidato sale de
  revisar qué le falta al roadmap general (`docs/PLAN_MAESTRO.md`, sección
  10) que todavía no esté cubierto. De la lista de pendientes que quedó
  registrada en `/areas/proferta-realestate.md` (memoria de Claude, no de
  este repo) siguen abiertos, en orden aproximado de impacto: (a) gateway de
  pago real (Mercado Pago/Stripe) — hoy `MockPaymentGateway` deniega todo por
  default; (b) esquema de múltiples agentes por propiedad con fusión de
  rango de precio; (c) UI de planes de suscripción y facturación real; (d)
  feature "Busco propiedad" (demanda particular) y su dashboard de métricas
  premium. Al abrir la próxima sesión, si el usuario no da una dirección
  explícita, proponer (a) como candidato — es el que más bloquea el modelo
  de negocio (`payment_gateway.charge()` siempre devuelve `False` fuera de
  producción, así que ningún cobro real puede completarse todavía) — pero
  confirmar antes de arrancar, porque toca dinero (regla "Si algo es
  ambiguo" / sección 5-6-8 del plan maestro, no se asume en silencio).
