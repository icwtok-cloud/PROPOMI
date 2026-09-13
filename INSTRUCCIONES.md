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

## Historial de etapas

| Etapa | Descripción | Archivos tocados | Commit | Estado |
|-------|-------------|-------------------|--------|--------|
| 000 | Creación de este archivo de instrucciones y reglas del proyecto | INSTRUCCIONES.md | etapa-000_instrucciones-iniciales | Pendiente de push |

## Próximo paso lógico (a ejecutar apenas se confirme este push)

- Revisar estructura actual de `apps/api` y `apps/web` para definir la etapa 001
  (probablemente: revisar contratos API existentes antes de tocar código, dado que
  el README menciona que faltan capas de producción: auth real, RBAC, rate limiting,
  migraciones Alembic, etc.)
