# MCP-MS-TODO-Server — Contributor Instructions (2025, authentik-first)

This document explains what this project does, how it works today, and how to continue development. It reflects the current codebase after a major refactor to delegate all authentication/authorization to authentik (OIDC). Prior designs are intentionally omitted.

--------------------------------------------------------------------------------

## Overview

- Purpose: A FastAPI-based MCP server that exposes Microsoft To Do (Microsoft Graph) operations via a JSON-RPC 2.0 interface at `/mcp` (tools/list, tools/call).
- AuthN/AuthZ: Fully delegated to authentik (OIDC) using token introspection; no API keys, no local token stores, no admin CRUD endpoints.
- Authorization: Casbin is used for tool-level authorization (policy model + optional DB-backed rules). Subjects are derived from authentik claims (user_id, role via scoped prefix, groups via claim).
- Streaming: Optional SSE over GET `/mcp` for tool output fan-out.
- Ops: Minimal operational endpoint `/ops/policy/reload` to reload Casbin policies.
- Metrics: Prometheus-style `/metrics` endpoint.

--------------------------------------------------------------------------------

## Runtime Model

- JSON-RPC: POST `/mcp`
  - `tools/list`: returns the tool manifest filtered by Casbin for the current user.
  - `tools/call`: validates input (jsonschema), enforces policy, invokes the mapped service, and returns normalized output.
  - Authentication: Bearer token issued by authentik.
- SSE: GET `/mcp` with `Accept: text/event-stream` opens a server-sent events stream; responses from tools/call are broadcast to connected clients.
- Health: GET `/health` (requires the same Bearer auth).
- Ops: POST `/ops/policy/reload` (admin Bearer required) to reload the Casbin enforcer.
- Metrics: GET `/metrics` (no auth; rely on reverse proxy if needed).

--------------------------------------------------------------------------------

## Authentication (authentik, OIDC)

- All authentication is via authentik access tokens (Bearer) verified using RFC 7662 introspection.
- Configuration (see `app/config.py`):
  - `AUTHENTIK_ENABLED`, `AUTHENTIK_ONLY` (set both true for OIDC-only mode)
  - `AUTHENTIK_INTROSPECTION_URL`, `AUTHENTIK_CLIENT_ID`, `AUTHENTIK_CLIENT_SECRET`
  - Role scope prefix: `AUTHENTIK_ROLE_PREFIX` (default `mcp.role:`)
  - Groups claim: `AUTHENTIK_GROUPS_CLAIM` (default `groups`)
  - Optional Graph token claims: `AUTHENTIK_GRAPH_ACCESS_CLAIM` / `AUTHENTIK_GRAPH_REFRESH_CLAIM`
- Admin: a token containing `AUTHENTIK_ADMIN_ROLE` (default `mcp.admin`) is treated as admin for protected ops (e.g., policy reload).
- No API keys are accepted anywhere. Legacy admin/user key endpoints and helpers have been removed.

--------------------------------------------------------------------------------

## Graph Access (Microsoft To Do)

- All tool implementations rely on a TokenProvider resolved in `app/container.py`.
- Provider: `app/infrastructure/token_provider_authentik.py` reads the current request user meta:
  - Preferred: `meta.graph.access_token` (if provided by authentik claims).
  - Fallback (strict mode): if `AUTHENTIK_ONLY=true` and no graph access token claim exists, the request fails; you may optionally allow bearer-as-graph in your authentik pipeline by mapping the same token under the configured claim.
- Repository: `app/infrastructure/msgraph_repository.py` wraps REST calls (see `app/adapter_graph_rest.py`).

--------------------------------------------------------------------------------

## Authorization (Casbin)

- Model: `policy/model.conf` (RBAC with wildcards).
- Storage: file or DB (table `casbin_rule`). Configure via env, e.g. `CASBIN_MODEL` + `CASBIN_STORE=db`.
- Subjects used by policy:
  - `user_id` from authentik subject
  - `role` from scope with prefix `AUTHENTIK_ROLE_PREFIX` (e.g., `mcp.role:lite` → `role=lite`)
  - `groups` from claim `AUTHENTIK_GROUPS_CLAIM`
- Where it’s enforced:
  - tools/list → filtered with `app.auth.policy.filter_tools_for()`
  - tools/call → rechecked with `app.auth.policy.enforce_tool()`
- Operational reload: `POST /ops/policy/reload` (admin token required)

--------------------------------------------------------------------------------

## Project Layout (current)

```
app/
  main.py                       # FastAPI app wiring (SSE, JSON-RPC, ops)
  tools.py                      # Tool registry, schemas, dispatch
  api/
    security.py                 # authentik-only auth
    routers/
      ops.py                    # /ops/policy/reload
  integrations/
    authentik.py                # OIDC introspection + meta mapping
  infrastructure/
    msgraph_repository.py       # Microsoft To Do (Graph) repository
    token_provider_authentik.py # Reads graph token from authentik meta
  usecases/                     # Business logic (TodoService etc.)
  auth/                         # Casbin policy wiring
  policy.py                     # Shim to app.auth.policy
  context.py, container.py, config.py, db.py, models.py (CasbinRule only)
policy/
  model.conf, policy.csv        # Casbin model + example policy
.github/instructions/           # This document
Makefile                        # Thin, authentik-first
```

Removed: any admin CRUD APIs, API key/token/app/group tables & code, helper CLIs, and legacy IdP integrations.

--------------------------------------------------------------------------------

## Local Development

- Prereqs: Python 3.10+, Node 18+ (for the sample client), Docker (for authentik stack).
- Start authentik (dev): `make authentik-up`
- Configure `.env` minimally, e.g.:
  - `AUTHENTIK_ENABLED=true`
  - `AUTHENTIK_ONLY=true`
  - `AUTHENTIK_INTROSPECTION_URL=http://localhost:9000/application/o/introspect`
  - `AUTHENTIK_CLIENT_ID=...`
  - `AUTHENTIK_CLIENT_SECRET=...`
- Start the server: `make dev-serve`
- Call tools with bearer:
  - `BEARER_TOKEN=<token> make mcp-tools`
  - `BEARER_TOKEN=<token> METHOD=tools/call PARAMS='{"name":"todo.lists.get","arguments":{}}' make mcp-call`
- Reload policy: `AUTHENTIK_TOKEN=<admin_token> make policy-reload`

--------------------------------------------------------------------------------

## Adding/Changing Tools

- Define tool JSON schemas under `app/tools/*.json`.
- Map behavior in `app/tools.py` (explicit or convention-based mapping to service methods).
- Keep input validation (jsonschema) and exceptions concise.
- Enforce authorization centrally via Casbin; do not add tool-specific allowlists in code.

--------------------------------------------------------------------------------

## Configuration Reference (selected)

- Server: `PORT`, `LOG_LEVEL`, `TOOL_SCHEMA_DIR`, `SSE_ENABLED`, etc.
- Authentik: `AUTHENTIK_*` variables as listed above.
- Casbin: `CASBIN_MODEL`, `CASBIN_STORE=db` (or `CASBIN_DB=true`).
- Metrics: `/metrics` endpoint is always on; place behind reverse proxy if needed.

--------------------------------------------------------------------------------

## Contribution Guidelines

- Auth: Never reintroduce API keys or local token stores. All identity flows must be via authentik.
- Secrets: Do not commit secrets. `.env` and `secrets/` are gitignored; use examples only.
- Style: Keep changes small, focused, and consistent with the current patterns (FastAPI + JSON-RPC + Casbin + authentik).
- Testing: Prefer small end-to-end tests that call `/mcp` with a valid bearer over unit tests that bypass the policy layer.
- Docs: Update `.github/instructions/` when altering auth, endpoints, or tool behavior.

--------------------------------------------------------------------------------

## Quick Checklist (for new contributors)

- [ ] Can run `make authentik-up` and obtain a bearer token from authentik
- [ ] Can run `make dev-serve` and get `/health`
- [ ] Can run `BEARER_TOKEN=... make mcp-tools`
- [ ] Added/updated tool schemas and mappings with validation
- [ ] Verified Casbin rules allow intended tools for your role/groups
- [ ] If changed policy storage, tested `/ops/policy/reload`
- [ ] Did not add API keys or local credential logic

