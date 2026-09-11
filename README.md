# PROPOMI · Full Product Architecture

Propomi convierte el interés inmobiliario en intención comercial estructurada.

## Las 5 fases están integradas
1. **Core / Discovery + Decision**: búsqueda, filtros, propiedades, detalle, comparación, favoritos, frescura/origen y capacidad de compra.
2. **Intent**: eventos, niveles de intención, perfil estructurado, preguntas, visitas y propuesta de precio.
3. **Agencies**: agencia, claim, verificación, oportunidades, solicitud de contacto y privacidad por defecto.
4. **Negotiation**: oferta, contraoferta, aceptar, rechazar, iniciar negociación y trazabilidad.
5. **Intelligence**: funnel, analytics y base de eventos para matching, recomendaciones, demanda y pricing intelligence.

## Stack
- Frontend: Next.js + TypeScript + React
- Backend: FastAPI + SQLAlchemy
- DB: SQLite local / PostgreSQL recomendado en Render
- Deploy: Vercel + Render
- DNS/SSL/WAF: Cloudflare
- Dominio: `propomi.lat`

## Ejecutar
### API
```bash
cd apps/api
python -m venv .venv
# activar entorno
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Web
```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Con `NEXT_PUBLIC_API_URL` vacío, el frontend funciona en modo demo usando fixtures locales. Con la API configurada, persiste eventos, intents, ofertas y oportunidades en la base de datos.

## Producción
En Render usar PostgreSQL y `DATABASE_URL`. En Vercel configurar `NEXT_PUBLIC_API_URL` apuntando a Render. En Cloudflare apuntar `propomi.lat` al frontend de Vercel y mantener el API en su subdominio.

## Importante
Esta versión une las cinco fases en una arquitectura funcional de producto. Para producción todavía deben agregarse autenticación real, RBAC/aislamiento de agencias, verificación de identidad empresarial, secretos gestionados, rate limiting, auditoría avanzada, crawler legal/robusto, almacenamiento de imágenes y migraciones Alembic. El núcleo de producto y sus contratos API quedan preparados para esas capas.
