## 2026-09-17 — ix_properties_hot v2 (patch quirúrgico)

- v1 defectuosa: zip con main.py completo de HEAD viejo, pisaba _bulk_group_info / _properties_base_stmt / GET /properties/random.
- v2: solo +27 líneas (ensure_schema_indexes + call). Entrega como .patch + snippet, sin main.py completo.
- Índice: CREATE INDEX IF NOT EXISTS ix_properties_hot ON properties (hidden_at, last_seen_at, priority_score DESC, detected_at DESC) WHERE hidden_at IS NULL.
