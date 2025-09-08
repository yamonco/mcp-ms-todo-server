---
sidebar_position: 6
---

# Deployment

## Docker Compose (recommended)
```bash
cp .env.example .env
make db-up
make app-register PROFILE=admin
make dev-serve         # dev
# or
make prod-up           # prod (compose direct)
```

Ensure `.env` has `ADMIN_API_KEY`, `DB_URL`, `ADMIN_*` configured. For prod, front with a reverse proxy and persistent volumes for DB.

## Environment
- API key is required for admin endpoints (`X-API-Key`).
- Tokens live in DB; no token files are mounted.

## Health & Metrics
- Health: `GET /health`
- Metrics: `GET /metrics` (Prometheus)

## Troubleshooting
- Check server logs and `LOG_LEVEL`
- Verify DB connectivity (`DB_URL`)
- Confirm app meta saved (`/admin/tokens/by-profile/<profile>`) and user API key created
