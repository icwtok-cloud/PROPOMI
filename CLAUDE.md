# Instrucciones para Claude (o cualquier IA) trabajando en este repo

## Frase de arranque (aplica en CUALQUIER sesión nueva, sin excepción)

El dueño del producto va a abrir sesiones nuevas de chat sin memoria previa
del repo (o con memoria de Claude.ai activada pero sin este archivo en
contexto) y va a decir simplemente algo como:

> "Acá está el repo (link o clonado local). Seguí las instrucciones."

Eso alcanza. No hace falta que repita nada más. Ante esa frase (o cualquier
variante equivalente: "segui las instrucciones", "continuemos", "retomemos
el repo"), la sesión tiene que **arrancar a ejecutar de una**, siguiendo los
4 pasos de más abajo, sin:
- Pedirle que reexplique el proyecto.
- Preguntar de nuevo por preferencias ya fijadas acá (Windows/PowerShell,
  versionado, zips, sin ambiente de test, sin Claude Code — ver más abajo).
- Tratar el pedido como ambiguo. No lo es: la ambigüedad la resuelve este
  archivo + `PROGRESS_LOG.md`, no una pregunta nueva al usuario.

Si estás leyendo esto porque el dueño del producto compartió este repo y dijo
algo como **"Seguí las instrucciones y continuemos"**, hacé esto en orden:

1. Leé completo `docs/PLAN_MAESTRO.md` — es el brief de negocio + producto +
   arquitectura completo. Asume que no sabés nada del proyecto. No te saltees
   secciones, en particular la sección 5 (reglas no negociables de privacidad)
   y la sección 11 (checklist de calidad).
2. Leé completo `PROGRESS_LOG.md` — ahí está el historial real de qué se
   entregó, en qué etapa del roadmap vamos, y qué decisiones se tomaron sobre
   la marcha. El roadmap oficial (orden de dependencia) está en la sección 10
   de `docs/PLAN_MAESTRO.md`; `PROGRESS_LOG.md` te dice en qué punto de ese
   roadmap está el repo HOY.
3. Confirmá con el usuario en qué etapa retomar (por default: la primera
   etapa del roadmap que no esté marcada como cerrada en `PROGRESS_LOG.md`).
4. Trabajá en partes chicas, un archivo o un grupo chico de archivos por vez
   — nunca prometas ni asumas cambios sobre archivos que no viste.

## Por qué existe este archivo

No hay una herramienta de código (Claude Code) conectada a este repo — el
trabajo se hace **exclusivamente en un chat normal de Claude.ai (o app),
nunca con acceso directo al repo del usuario**. El repo puede estar clonado
en la máquina del usuario o accesible públicamente en GitHub, pero quien
edita, versiona y pushea archivos siempre es el usuario, a mano, con los
comandos que Claude le da listos para copiar/pegar.

**Tampoco hay ambiente de test instalado en la máquina del usuario.** Ni
`pytest` ni `npm run build` se pueden correr localmente antes de pushear.
Esto es una limitación permanente, no algo a resolver en una etapa futura.
Consecuencias concretas para cómo trabajar:
- El checklist de calidad de la sección 11 del plan maestro **no se puede
  verificar corriendo los comandos** — hay que aplicarlo por revisión
  manual/lectura del código antes de entregar cada archivo (imports
  completos, sintaxis válida, nombres de funciones/rutas consistentes con
  el resto del archivo, etc.).
- Cualquier cambio se entrega asumiendo que el primer despliegue real (en
  Render/Vercel) es también la primera vez que ese código corre. Si algo
  falla ahí, el usuario pega el error de log en el chat y se corrige en la
  siguiente versión — no hay forma de detectarlo antes.
- Por eso mismo, los cambios grandes conviene partirlos en versiones chicas
  y probables de andar, en vez de una reescritura enorme de una sola vez.

El flujo real, en orden, es siempre:

1. El usuario pega o sube el archivo puntual del repo que hay que tocar para
   la etapa en curso (ej. `apps/api/app/main.py` para agregar un modelo
   nuevo), o Claude ya lo tiene clonado en su propio sandbox si el repo es
   público (puede leerlo, pero no editarlo ahí para el usuario — igual
   entrega el archivo completo por chat).
2. Claude devuelve el archivo completo listo para reemplazar (nunca un
   diff/parche), respetando el checklist de la sección 11 del plan maestro
   aplicado por revisión manual (ver limitación de arriba).
3. Claude entrega, junto con el archivo, los **comandos exactos de
   PowerShell** para copiar el archivo a su ruta real dentro del repo,
   hacer `git add` / `git commit` / `git push` — ver reglas de entrega más
   abajo. El usuario los pega tal cual, sin adaptar nada.
4. Después de cada push confirmado por el usuario, Claude agrega una
   entrada nueva en `PROGRESS_LOG.md` (fecha, qué se hizo, qué falta, qué
   decisiones quedaron tomadas) — esto es lo que le permite a una sesión
   futura, con cero contexto previo, retomar exactamente donde quedó.

## Versión de este archivo: v5

## Trabajar en partes CHICAS (regla nueva, crítica)

El usuario reportó que sesiones largas de código se cortan antes de
terminar, obligándolo a empezar de cero en una sesión nueva sin haber
llegado a pushear nada. Para evitar esto:

- **Nunca encarar una etapa completa del roadmap en un solo tramo largo de
  código.** Cortar el trabajo en entregas chicas: un archivo (o 2-3 como
  mucho si son chicos y muy relacionados) por vez, cada una con su propio
  cierre — comandos de PowerShell listos y entrada de `PROGRESS_LOG.md` —
  ANTES de pasar al siguiente archivo de esa misma etapa.
- Si una etapa completa requiere tocar 5 archivos, eso son potencialmente
  5 entregas chicas separadas (o menos si el usuario prefiere agruparlas),
  no una entrega única al final. Preguntar o proponer el corte en partes
  antes de arrancar si la etapa se ve grande.
- Cada parte chica tiene que quedar **pusheable de forma independiente** —
  nunca depender de "esto no sirve de nada hasta que llegue la parte 3".
  Si una etapa no se puede partir así sin dejar el repo en un estado roto a
  medio camino, avisar eso explícitamente y proponer el corte menos malo
  (ej. back-end primero y funcionando solo, front-end después).
- Esto tiene prioridad sobre entregar "el paquete completo" de una sola vez
  — la sección 11 del plan maestro pide paquete completo por ETAPA, no que
  toda la etapa se escriba y explique en una sola respuesta larga.

## Reglas que nunca se rompen (resumen — el detalle está en la sección 5 del plan maestro)

- El comprador nunca escribe texto libre para condiciones de compra.
- El agente nunca responde con texto libre (solo acciones estructuradas).
- Todo campo de comentario nuevo pasa por `sanitize_free_text()`.
- `buyer_name` / `buyer_phone` / `buyer_email` nunca viajan en una respuesta
  de API salvo `contact_revealed = true`.
- Identidad canónica de agente = teléfono E.164, no email.
- Canal B2B agente↔agente es siempre gratis y no puede usarse para reenviar
  un contacto de comprador ya capturado por el canal B2C pago.

## Cómo entregar cada etapa (reglas fijas, no volver a preguntar)

Rutas fijas de este usuario, ya confirmadas — usar siempre estas, sin
preguntar de nuevo:
- Repo local: `$env:USERPROFILE\Documents\PROPOMI`
- Todo archivo que Claude entregue para descargar cae en:
  `$env:USERPROFILE\Downloads`

Reglas de entrega, todas obligatorias:

1. **Windows + PowerShell siempre.** El usuario copia y pega, no adapta
   nada. Nunca dar comandos de bash/mac ni pedirle que "reemplace la ruta"
   — usar `$env:USERPROFILE\...` para que se resuelva solo.
2. **Versionado creciente por archivo — y esto aplica también a los
   archivos "fijos" como `CLAUDE.md` y `PROGRESS_LOG.md`.** Nunca repetir
   un nombre de descarga que ya se usó antes en la conversación, ni
   siquiera para un archivo que en el repo siempre se llama igual —
   Windows le agrega automáticamente `(1)`, `(2)`, etc. al repetirse, y
   eso obliga al usuario a borrar el archivo viejo y renombrar el nuevo a
   mano cada vez. Regla concreta:
   - Todo archivo que se entregue para bajar lleva un sufijo de versión
     único en el nombre de descarga: `main_v2.py`, `main_v3.py`,
     `CLAUDE_v2.md`, `CLAUDE_v3.md`, `PROGRESS_LOG_v4.md`, etc.
   - El paso de PowerShell que lo copia al repo es el que le pone el
     nombre final correcto (`CLAUDE.md`, sin sufijo) vía `Copy-Item
     -Destination` — el usuario nunca tiene que renombrar nada a mano.
   - El número de versión de cada archivo es propio de ESE archivo, no un
     contador global del proyecto (ver regla de versionado más abajo,
     donde ya se explica esto para el código).
3. **Si la entrega incluye más de un archivo, empaquetar en un .zip** y
   los pasos de PowerShell tienen que incluir la extracción
   (`Expand-Archive`) antes de copiar cada archivo a su carpeta real dentro
   del repo — nunca asumir que el usuario sabe descomprimir y ubicar cada
   uno a mano.
4. **Los pasos de push van siempre completos y listos para pegar:** entrar
   a la carpeta del repo, copiar/mover cada archivo a su ruta real dentro
   de `apps/...`, `git add` de esos paths puntuales, `git commit` con un
   mensaje que incluya la etapa y la versión (ej. `"Etapa 1 v2: modelo de
   datos ampliado"`), `git push origin main`.
5. **Después de cada push confirmado, sumar una entrada nueva en
   `PROGRESS_LOG.md`** (nunca reemplazar entradas viejas) con lo que se
   hizo, qué versión de qué archivo quedó pusheada, y qué sigue.

## Si algo es ambiguo

No asumas en silencio, en especial en todo lo que toca privacidad de
contacto (sección 5) o dinero (secciones 6 y 8). Para el resto, la sección
6.2 del plan maestro ya trae defaults recomendados explícitos — usalos y
avisá que son reversibles, no te bloquees esperando confirmación.
