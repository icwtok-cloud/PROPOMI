# Auditoría frontend apps/web — 2026-09-15

## Alcance
`apps/web/components/**`, `apps/web/app/**`, `apps/web/lib/**`.

## Método
- Grep de mojibake (`Ã©`, `â€`, etc.)
- Conteo `style={{` por archivo
- Grafo de imports de componentes
- Revisión de `catch{}` vacíos y `req()` en `lib/api.ts`
- Intento de `tsc --noEmit` (ver sección Validación)

---

## 1. Encoding roto

| Archivo | Hallazgo | Severidad |
|---|---|---|
| — | No se encontraron secuencias mojibake reales. Matches de “Financiaci” eran UTF-8 correcto (`Financiación`). | — |

**OfferModal.tsx:** no existe en el repo (reemplazado por `IntentWizard`).

---

## 2. Estilos inline vs globals.css

| Archivo | `# style={{` | Severidad | Nota |
|---|---|---|---|
| `admin/page.tsx` | 23 | Media | Panel interno; layout ad-hoc |
| `AgentDashboard.tsx` | 16 | Media | Modal/filas de props; migrable |
| `IntentWizard.tsx` | 13 | Media | Wizard denso |
| `onboarding/[token]/page.tsx` | 11 | Baja | Flujo puntual |
| `admin/login/page.tsx` | 7 | Baja | Login simple |
| `tienda/[slug]/page.tsx` | 6 | Baja | |
| `page.tsx` | 5 | Baja | |
| `AgentLead/OfferActions` | 2 c/u | Baja | |
| `DemandPanel.tsx` | 1 | Cosmética | Solo `width` dinámico de barra (legítimo) |
| `PropertyCard.tsx` | 2 | Baja | |

**Prioridad futura:** AgentDashboard + IntentWizard + admin/page.  
**No se migraron todos** en este encargo (volumen medio/bajo).

---

## 3. Fetch sin feedback al usuario

`lib/api.ts` → `req()` **sí lanza** Error con `status` si `!r.ok` (bien).

| Ubicación | Problema | Severidad | Acción |
|---|---|---|---|
| `app/page.tsx` carga catálogo | `catch{}` vacío → listado vacío sin mensaje | **Alta** | **Corregido:** `loadError` + notice |
| `app/page.tsx` ofertas comprador | `catch{}` | Media | Log `console.warn` (no bloquea UI) |
| `app/page.tsx` filtros | `catch{}` | Baja | Log warn |
| `AgentDashboard.tsx` carga panel | `.catch(()=>{})` | **Alta** | **Corregido:** `setError(...)` |

Resto de pantallas admin/onboarding/wizard: tienen try/catch con mensaje.

---

## 4. Código muerto

| Archivo | Estado | Severidad |
|---|---|---|
| `components/AgentLeadActions.tsx` | **No importado** desde ningún lado | Media (deuda) |
| OfferModal / BuyerIdentityModal | Solo mención en comentario de IntentWizard | — |

**No se borró** AgentLeadActions en este paquete (puede reutilizarse si el dashboard vuelve a listar leads con acciones separadas). Documentado para encargo de limpieza.

---

## 5. tsc --noEmit

**Intentado** en este entorno:
- Node/npm disponibles (`/usr/bin/node`).
- `npm install` incompleto / timeouts de sandbox (typescript sin `lib/tsc.js` usable).
- **No se obtuvo un reporte limpio de tsc** en esta sesión.

Recomendación: correr en CI o local:
```bash
cd apps/web && npm ci && npx tsc --noEmit
```

---

## Fixes aplicados en este paquete (solo severidad alta)

1. `apps/web/app/page.tsx` — error visible si falla la carga de propiedades.  
2. `apps/web/components/AgentDashboard.tsx` — error visible si falla la carga del panel.

El resto queda listado arriba para encargos futuros.
