# --- insertar ANTES de migrate_legacy_property_images() en apps/api/app/main.py ---

def ensure_schema_indexes() -> None:
    """Índices parciales que aceleran el listado home / random / freshness.

    ix_properties_hot soporta el filtro típico:
      hidden_at IS NULL AND last_seen_at >= cutoff
      ORDER BY priority_score DESC, detected_at DESC
    sin seq scan de toda la tabla properties.

    CREATE INDEX IF NOT EXISTS (no CONCURRENTLY): corre dentro de
    engine.begin() al arranque; CONCURRENTLY no puede ir en transacción.
    IF NOT EXISTS es idempotente y seguro en restarts con datos ya cargados.
    """
    inspector = inspect(engine)
    if not inspector.has_table("properties"):
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_properties_hot "
                "ON properties (hidden_at, last_seen_at, priority_score DESC, detected_at DESC) "
                "WHERE hidden_at IS NULL"
            )
        )


# --- en el bloque de startup, inmediatamente después de ensure_schema_columns(): ---
# ensure_schema_columns()
# ensure_schema_indexes()   <-- agregar esta línea
# migrate_legacy_property_images()
