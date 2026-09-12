# Propomi API

FastAPI + SQLAlchemy backend for all five product phases.

## Layers
- Discovery: properties/search/detail/source freshness
- Decision: intent profiles and event tracking
- Agencies: claim/verification/opportunities
- Negotiation: offers/counteroffers/status transitions/contact consent
- Intelligence: funnel/analytics endpoints ready for future scoring/recommendations

Defaults to SQLite for local development. Set `DATABASE_URL` to Postgres on Render for production.
