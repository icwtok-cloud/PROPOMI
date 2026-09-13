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

## Convención de nombres de commit / reversión

Formato: `etapa-NNN_<descripcion-corta>` y su reversión `revert-etapa-NNN_<descripcion-corta>`

## Versionado de archivos entregados (para no pisar descargas)

| Archivo (nombre real en el repo) | Última versión de descarga entregada |
|---|---|
| INSTRUCCIONES.md | V6 |
| apps/web/lib/types.ts | V1 |
| apps/web/lib/api.ts | V1 |
| apps/web/components/AgentDashboard.tsx | V1 |
| apps/web/components/PropertyCard.tsx | V1 |
| apps/web/app/globals.css | V1 |

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

## Próximo paso lógico (candidato para etapa 007)

- Confirmar visualmente el flujo de oferta: revisar `OfferModal.tsx` y
  `BuyerIdentityModal.tsx` (raw links todavía no obtenidos — no aparecen en el
  manifiesto probado hasta ahora, hay que pedirlos puntualmente al usuario una
  vez más, o pedirle que fetchee `INSTRUCCIONES.md` primero) para confirmar que
  el frontend bloquea visualmente "Enviar oferta" hasta tener celular + Google
  verificados (el backend en `POST /offers` ya lo exige de todas formas — esto
  es una mejora de UX, no un fix de seguridad).
