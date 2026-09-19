# Diseño — Agente → Agente ("Sugerir otra propiedad")

Fecha: 2026-09-16
Estado: **diseño únicamente, sin código todavía.**

## Por qué existe este documento

El home de Propomi ya promete esta función ("Sugerir otra propiedad", listada
junto a "Solicitar contacto" y "Aceptar o proponer visita" en la sección de
Agencias). Se auditó `apps/api/app/main.py` completo y **no existe ningún
endpoint ni tabla para esto** — es copy de marketing sobre una función que
todavía no se construyó.

## Caso de uso

Un comprador ofertó/consultó sobre la Propiedad A de la Agencia 1. La
Agencia 1 no tiene nada mejor para ese presupuesto/zona, pero sabe (o el
sistema puede inferir) que la Agencia 2 sí tiene algo que calza. Hoy ese
comprador se pierde. La función deja que la Agencia 1 le muestre al
comprador una propiedad de la Agencia 2 sin filtrar el contacto del
comprador a la Agencia 2 automáticamente (mismo principio de privacidad por
defecto que rige el resto del producto).

## Decisiones de diseño (a confirmar con el dueño del producto)

1. **¿Quién sugiere?** Solo la Agencia 1 (dueña de la oportunidad original)
   puede sugerir, no cualquier agencia puede ofrecerse espontáneamente sobre
   una oportunidad ajena — evita spam entre agencias competidoras.
2. **¿El comprador ve quién sugirió?** Sí, transparencia: "Te sugerimos esta
   propiedad de [Agencia 2] porque puede ajustarse mejor a tu búsqueda."
3. **¿Se comparte el contacto del comprador con la Agencia 2?** NO
   automáticamente. La sugerencia crea una nueva "oportunidad" visible para
   la Agencia 2 recién SI el comprador hace click y muestra interés
   (ver/guardar/ofertar) sobre la propiedad sugerida — mismo funnel de
   intención que ya existe para cualquier propiedad.
4. **¿Hay límite para evitar abuso?** Sí — tope diario de sugerencias por
   agencia (mismo patrón de `_rate.try_hit` que ya usa `demand_match`),
   para que no se use como canal de spam cruzado entre agencias.

## Modelo de datos propuesto

```python
class PropertySuggestion(Base):
    __tablename__ = "property_suggestions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_offer_id: Mapped[str | None]      # oferta/lead original que motivó la sugerencia
    source_property_id: Mapped[str]          # propiedad sobre la que estaba el comprador
    suggested_property_id: Mapped[str]       # propiedad de la OTRA agencia
    suggesting_agency_id: Mapped[str]        # quién sugiere (Agencia 1)
    target_agency_id: Mapped[str]            # dueña de la propiedad sugerida (Agencia 2)
    buyer_session_id: Mapped[str]            # a quién se le muestra (sesión/usuario comprador)
    status: Mapped[str] = mapped_column(default="SENT")  # SENT | VIEWED | ENGAGED | DISMISSED
    created_at: Mapped[datetime]
```

## Endpoints propuestos

- `POST /properties/{property_id}/suggest` — body `{suggested_property_id}`,
  requiere sesión de agente dueño de `property_id`. Valida:
  - `suggested_property_id` pertenece a OTRA agencia (si no, 400).
  - Rate limit diario por agencia (evitar spam).
  - Crea `PropertySuggestion(status=SENT)`.
- `GET /buyers/me/suggestions` — el comprador (sesión guest o verificada) ve
  sus sugerencias pendientes, para mostrarlas en el detalle de la propiedad
  original o en una notificación in-app.
- `POST /property-suggestions/{id}/engage` — se llama automáticamente cuando
  el comprador hace click / guarda / oferta sobre `suggested_property_id`;
  pasa `status=ENGAGED` y **recién ahí** se genera un `Event` visible para
  `target_agency_id` en su pestaña Oportunidades (mismo patrón que
  `demand_match`, sección 6.2 del plan maestro: nunca se expone el contacto
  del comprador de entrada).

## Frontend

- En el detalle de propiedad / offercard del lado del comprador: si existe
  una `PropertySuggestion(status=SENT)` para esa sesión, mostrar una tarjeta
  "Te puede interesar" con la propiedad sugerida y de qué agencia viene la
  recomendación.
- En `AgentDashboard.tsx`, pestaña Propiedades: botón "Sugerir a otro
  comprador" sobre cada propiedad propia, que abre un buscador acotado a
  propiedades de OTRAS agencias (mismo `getProperties` con filtro
  `exclude_agency_id`).

## Por qué no se construye ahora

Es una feature nueva de punta a punta (tabla, 3 endpoints, UI en dos
lugares distintos, reglas anti-abuso) — no es un ajuste chico como el resto
de lo tocado en esta sesión. Queda lista para pasar a construcción en una
etapa dedicada.
