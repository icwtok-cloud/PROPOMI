# INSTRUCCIONES DEL PROYECTO — PROPOMI

> Este archivo es la memoria persistente entre sesiones. Al iniciar una nueva sesión,
> el usuario solo pasa el link del repo y dice "seguí las instrucciones". Claude debe
> leer este archivo primero, ubicar en qué etapa quedó el proyecto, y continuar sin
> pedir que se repitan estas reglas.

## Reglas de trabajo (fijas, no se repiten)

1. El usuario abre sesión enviando el repo. Se debe continuar exactamente donde quedó
   la última sesión (ver sección "Historial de etapas" abajo).
2. No hay CLI ni conexión directa al repo desde Claude. El usuario tiene el repo
   clonado localmente y pushea manualmente. Claude nunca asume que puede pushear él mismo.
3. Cada archivo entregado para pushear va acompañado de los comandos exactos de
   PowerShell (Windows) para que el usuario los copie y pegue tal cual.
4. Cada actualización/push, por mínimo que sea, se anota en la sección "Historial de
   etapas" de este archivo (fecha lógica de la etapa, qué se hizo, archivos tocados).
5. Cada nueva actualización debe tener un nombre de commit/reversión claro y
   descriptivo (convención abajo), para poder revertir puntualmente si hace falta.
6. Toda instrucción o regla nueva que dé el usuario se anota en este archivo antes
   de seguir, para que persista en próximas sesiones.
7. Claude decide el próximo paso lógico de construcción por su cuenta. No debe
   consultarle al usuario "qué sigue" — solo ejecutar y avisar qué hizo.
8. Las etapas de construcción deben ser PEQUEÑAS (cambios acotados), para no perder
   progreso si una sesión se corta a mitad de camino.

## Convención de nombres de commit / reversión

Formato: `etapa-NNN_<descripcion-corta>` y su reversión `revert-etapa-NNN_<descripcion-corta>`

Ejemplo:
- Commit: `etapa-004_agrega-endpoint-ofertas`
- Reversión asociada: `revert-etapa-004_agrega-endpoint-ofertas`

## Cómo Claude accede al código en cada sesión (regla de método, agregada por el usuario)

- No hay CLI ni conexión de Claude al repo. Claude NO puede fetchear URLs "raw" que
  él mismo construya: su herramienta de lectura web solo abre URLs que ya aparecieron
  antes en la conversación (por búsqueda o por mensaje del usuario).
- Por eso, el usuario debe pegar directamente los links raw de GitHub de los archivos
  relevantes, con este formato (sacar `/blob/` y cambiar el dominio):
  `https://github.com/<user>/<repo>/blob/<rama>/<ruta>`
  → `https://raw.githubusercontent.com/<user>/<repo>/<rama>/<ruta>`
- Para saber qué archivos existen en una carpeta, el usuario corre en PowerShell
  parado en la raíz del repo: `Get-ChildItem -Recurse .\apps\web -Name` (o la carpeta
  que corresponda) y pega el resultado.
- Al iniciar sesión, si Claude necesita ver contenido de archivos para decidir el
  siguiente paso, debe pedir puntualmente esos raw links (no relanzar todas las
  preguntas de reglas generales, que ya están accesibles acá).

## Historial de etapas

| Etapa | Descripción | Archivos tocados | Commit | Estado |
|-------|-------------|-------------------|--------|--------|
| 000 | Creación de este archivo de instrucciones y reglas del proyecto | INSTRUCCIONES.md | etapa-000_instrucciones-iniciales | Pendiente de push |
| 001 | Fix de contrato API↔Web: `types.ts` no tenía `images[]` ni `originPublishedAt` que el backend (`prop_dict` en main.py) ya devuelve hace etapas. También se completó el tipo `Agency` (faltaban `verificationStatus`, `instagram`, `websiteLink`, `freeLeadsRemaining`, ya usados por el backend) y se agregó `'search_performed'` a `EventName`. | apps/web/lib/types.ts | etapa-001_fix-contrato-property-agency-types | Pendiente de push |

## Próximo paso lógico (candidato para etapa 002)

- Revisar `components/PropertyCard.tsx` y `components/AgentDashboard.tsx` para
  confirmar si ya consumen `images`/`originPublishedAt`/los campos nuevos de
  `Agency`, o si quedaron mostrando solo `image` (singular) y datos de agencia
  incompletos — típico arrastre de la misma deuda que se corrigió en la etapa 001.
  Requiere que el usuario pase los raw links de esos dos componentes en la próxima
  sesión si no están ya disponibles en el historial de la conversación.
