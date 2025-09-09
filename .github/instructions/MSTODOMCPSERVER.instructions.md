
# MCP-MS-TODO-Server — Contributor Instructions (2025, Makefile Onboarding, OIDC-only)

This document describes the current architecture, onboarding, and development workflow for MCP-MS-TODO-Server. All onboarding, admin, and test flows are automated via Makefile targets. All authentication/authorization is OIDC-only (authentik). Legacy instructions are obsolete.

--------------------------------------------------------------------------------


## Overview

- FastAPI-based MCP server exposing Microsoft To Do (Graph) via JSON-RPC 2.0 `/mcp` (tools/list, tools/call)
- AuthN/AuthZ: OIDC-only (authentik), token introspection, no local keys or admin DB
- Tool-level RBAC: Casbin (file/DB), subjects from OIDC claims (user, role, group)
- All onboarding/admin/test flows automated via Makefile targets
- Streaming: Optional SSE `/mcp` (GET)
- Ops: `/ops/policy/reload` (admin only)
- Metrics: `/metrics` (Prometheus)

--------------------------------------------------------------------------------


## Runtime Model

- JSON-RPC: POST `/mcp` (tools/list, tools/call)
- SSE: GET `/mcp` (Accept: text/event-stream)
- Health: GET `/health` (Bearer required)
- Ops: POST `/ops/policy/reload` (admin only)
- Metrics: GET `/metrics` (no auth)

--------------------------------------------------------------------------------


## Authentication & Authorization (OIDC-only)

- All authentication is via authentik OIDC access tokens (Bearer, introspection)
- Admin: token must include `mcp.admin` (scope or role)
- Casbin: RBAC for tool access, subjects from OIDC claims (user, role, group)
- No local API keys, no admin DB, no legacy endpoints

--------------------------------------------------------------------------------


## Microsoft Graph Access

- All tools use a TokenProvider (see `app/container.py`)
- OIDC claim `meta.graph.access_token` preferred; fallback/strict mode per config
- REST calls via `app/infrastructure/msgraph_repository.py`

--------------------------------------------------------------------------------


## Casbin RBAC

- Model: `policy/model.conf` (RBAC)
- Storage: file or DB (`casbin_rule`)
- Subjects: user_id, role (from OIDC), group (from OIDC)
- Enforced on tools/list, tools/call
- Reload: `make policy-reload` (admin only)

--------------------------------------------------------------------------------


## Project Structure

- `app/` — FastAPI, domain, infra, OIDC, Casbin
- `policy/` — Casbin model/policy
- `client/` — sample client
- `Makefile` — all onboarding/ops automated
- `secrets/` — generated keys/tokens/app info (auto)

--------------------------------------------------------------------------------


## Local Development & Onboarding (Makefile-driven)

1. Configure `.env` (see example, set Authentik/MCP/Graph values)
2. Start dev server (auto port, auto authentik):
  ```
  make dev-serve
  ```
  Or background: `make dev-up-bg`, stop: `make dev-stop`, status: `make dev-status`
3. Onboard app/token/user key (all automated):
  ```
  make onboard PROFILE=alice USER_ID=alice ROLE=role:lite TOKEN_JSON=token.json
  ```
  Or stepwise: `make admin-app`, `make token-upsert ...`, `make apikey-add ...`
  Or OIDC-only: `make onboard-auth PROFILE=alice USER_ID=alice ROLE=role:lite`
4. Check admin access:
  ```
  make auth-check
  ```
5. Test API with last user key:
  ```
  METHOD=tools/list make mcp-tools-key USER_API_KEY="$(cat secrets/last_user_key)"
  ```
6. Clean/reset:
  ```
  make dev-clean
  make authentik-reset
  ```

--------------------------------------------------------------------------------


## Adding/Changing Tools

- Define tool schemas: `app/tools/*.json`
- Map in `app/tools.py`
- Validate with jsonschema
- Enforce all authz via Casbin (no hardcoded allowlists)

--------------------------------------------------------------------------------


## Key Configuration

- Server: `PORT`, `LOG_LEVEL`, `TOOL_SCHEMA_DIR`, `SSE_ENABLED`, etc.
- Authentik: `AUTHENTIK_*` variables
- Casbin: `CASBIN_MODEL`, `CASBIN_STORE=db`
- Metrics: `/metrics` (always on)

--------------------------------------------------------------------------------


## Contribution Guidelines

- Auth: OIDC-only (authentik), no local keys or DB
- Secrets: never commit `.env` or `secrets/`
- Style: small, focused, consistent with FastAPI + JSON-RPC + Casbin + authentik
- Testing: prefer end-to-end with real policy
- Docs: update `.github/instructions/` for any workflow change

--------------------------------------------------------------------------------


## Quick Checklist (for new contributors)

- [ ] Can run `make dev-serve` (or `make dev-up-bg`)
- [ ] Can run `make onboard ...` and get user API key
- [ ] Can run `make auth-check` (admin access)
- [ ] Can test API with last user key
- [ ] Can update tool schemas/mappings
- [ ] Can reload Casbin policy
- [ ] Never add local keys or DB auth logic

