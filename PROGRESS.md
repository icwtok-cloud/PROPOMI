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

### 2026-09-13 — `AgencyPhone` (backend)
- Nueva tabla `agency_phones` (id, agency_id, phone, verified_at, created_at) — telefonos adicionales de una agencia (celular personal + linea de oficina) sin tocar la columna `Agency.phone` existente (queda como telefono principal).
- `find_agency_by_phone()`: helper que busca una agencia por `Agency.phone` o por cualquiera de sus `AgencyPhone`.
- `POST /auth/otp/verify` ahora reconoce login desde un telefono secundario (antes solo miraba `Agency.phone`).
- `POST /agencies/{id}/relink-by-phone` ahora vincula publicaciones contra **todos** los telefonos de la agencia, no solo el que se uso para loguearse.
- Nuevos endpoints: `GET /agencies/{id}/phones` (lista principal + extras) y `POST /agencies/{id}/phones` (agrega uno nuevo; rechaza si ya pertenece a otra agencia con 409, o si no es tu agencia con 403).
- Bug encontrado y corregido (no relacionado a AgencyPhone pero lo destapo un test nuevo): `verify_otp` comparaba un datetime naive (como lo devuelve SQLite) contra uno con timezone y tiraba `TypeError` — pasaba desapercibido porque los tests existentes creaban sesiones directo con `create_token()`, sin pasar por el flujo real de OTP.
- 3 tests nuevos agregados a `test_security.py`: alta de telefono secundario + login funciona con el, rechazo de telefono ya usado por otra agencia, rechazo de alta sobre una agencia ajena. **11/11 tests pasan.**
- Pendiente (siguiente pedacito): UI en "Mi cuenta" del dashboard de agencia para cargar un telefono adicional desde la pantalla (hoy el endpoint existe pero no hay boton).

**Push de este cambio:**
```
cd PROPOMI
git checkout main
git pull origin main
git am 0002-agencyphone-backend.patch
git push origin main
```
