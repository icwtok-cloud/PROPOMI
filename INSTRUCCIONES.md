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
10. **Manifiesto de archivos (raw links)**: Claude no puede construir ni adivinar
    URLs raw de GitHub — su herramienta solo puede abrir URLs que ya aparecieron
    antes en la conversación (mensaje del usuario, o texto dentro de un archivo ya
    fetcheado). Por eso, todo raw link de un archivo del repo que el usuario haya
    pasado alguna vez queda anotado permanentemente en la sección "Manifiesto de
    archivos del repo" de este documento. Como ESTE archivo se fetchea al inicio de
    cada sesión, los links quedan disponibles para Claude sin que el usuario tenga
    que volver a pegarlos. Si Claude necesita un archivo que todavía no está en el
    manifiesto, ahí sí debe pedir puntualmente ese raw link (y agregarlo al
    manifiesto en cuanto lo reciba).

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
| INSTRUCCIONES.md | V3 |
| apps/web/lib/types.ts | V1 |

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
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/globals.css
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/app/agencia/page.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/AgentDashboard.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/AgentOfferActions.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/BuyerIdentityModal.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/ComparePanel.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/DemandPanel.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/OfferModal.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/components/PropertyCard.tsx
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/api.ts ✅ (ya leído)
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/data.ts
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/google.ts
- https://raw.githubusercontent.com/icwtok-cloud/PROPOMI/main/apps/web/lib/types.ts ✅ (ya leído, ya corregido en etapa 001)

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

## Próximo paso lógico (candidato para etapa 003)

- Con el manifiesto ya cargado, Claude debe intentar abrir directamente
  `components/PropertyCard.tsx` y `components/AgentDashboard.tsx` (sin pedírselos
  al usuario) para confirmar si ya consumen `images`/`originPublishedAt`/los campos
  nuevos de `Agency` corregidos en la etapa 001, o si quedaron mostrando solo
  `image` (singular) y datos de agencia incompletos.
