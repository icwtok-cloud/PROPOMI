# Propomi — Notas de avance

Registro de cambios pusheados, en orden. Cada entrada = un cambio ya probado y subido a `main`.
Roadmap completo de referencia: ver Documento Maestro (secciones 10 y 11).

## Convención de este archivo
Cada entrada pusheable incluye, al final, los comandos exactos de `git` para traer el cambio a tu máquina y pushearlo. Vos ejecutás el push; acá se deja preparado el commit.

## Etapa 1 — Limpieza + modelo de datos ampliado (en curso)

### Nota — intento previo descartado
Hubo un intento anterior de "Etapa 1" (commit `d97f2a6`, hecho con otra IA) que fue revertido (`eeaa564`) por venir incompleto. Confirmado con el dueño del producto: no tenía nada recuperable. No se retoma nada de ese intento.

### 2026-09-13 — Limpieza de repo
- Eliminada la carpeta duplicada `apps/apps` (contenido era copia vieja de `apps/web`/`apps/api`, confirmado no identico en `page.tsx` pero la version de `apps/web` es la correcta: cierra el modal de detalle antes de abrir pregunta/visita, la copia vieja no lo hacia).
- `apps/api/test_propomi.db` deja de trackearse (era un artefacto de test, no deberia estar en el repo).
- `.gitignore` actualizado: agregado `test_propomi.db` y `*.db`.
- Bug encontrado y corregido: `apps/api/requirements.txt` no incluia `phonenumbers` (usado en `main.py` para la identidad canonica del agente) — un clone limpio + `pip install -r requirements.txt` rompia al importar. Agregado `phonenumbers==8.13.55`.
- Verificado: 8/8 tests de `apps/api/tests/test_security.py` siguen pasando.
- Pendiente en esta etapa: `AgencyPhone`, `Property.images` como lista, `verification_status` en dos niveles, `Subscription`, `LeadCredit`.

**Push de este cambio:**
Este commit se armó en la sesión de Claude, no en tu máquina. Se entrega como archivo `.patch` para aplicar sobre tu copia local del repo:
```
cd PROPOMI
git checkout main
git pull origin main
git am 0001-etapa1-parte1-limpieza-apps-apps.patch
git push origin main
```
`git am` aplica el commit tal cual (mismo mensaje, mismo autor) — no un merge manual. Si da conflicto, avisame y ajusto el patch.
