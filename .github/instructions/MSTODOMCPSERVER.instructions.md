# MCP-MS-ToDo-Server — Agent Onboarding & Operating Guide

Audience: Coding agents and maintainers who will read, run, extend, or debug this repository with minimal friction. This guide is opinionated, task-oriented, and designed to be safe and repeatable in both local and production-like environments.

--------------------------------------------------------------------------------

## 0) Core Principles (Read First)

1) Always run commands from the repository root
   - Verify with `pwd` first. Expected: a path ending with `mcp-ms-todo-server`.
   - Many Make targets assume repo-root relative paths.

2) Prefer Make targets over raw commands
   - Make encapsulates default flags, environment wiring, and common flows.
   - Example: use `make dev-serve` instead of hand-writing a uvicorn command.

3) Keep configuration out of code
   - Use `.env` (server) and `tests/.env` (test smoke) for secrets and settings.
   - Never hardcode secrets; rely on env variables or Make target injection.

4) Casbin is the single source of authorization
   - Tool visibility (tools/list) and execution (tools/call) are enforced by Casbin.
   - File- and DB-backed policies are both supported. Defaults are seeded.

5) Idempotent bootstrap
   - First-start auto-creates DB schema (if configured) and seeds default groups/policies.
   - Admin APIs are split by domain for clarity and safer extension.

--------------------------------------------------------------------------------

## 1) Repository Layout (High Level)

```
app/
  main.py                  # FastAPI app: MCP endpoints + router include + metrics
  tools.py                 # Tool registry, param validation, execution
  auth/                    # Casbin (file/DB) enforcement
    policy.py              # Enforcer wiring, filter/enforce, auto-seed defaults
    adapter_sqlalchemy.py  # DB adapter (read-only load from casbin_rule)
  api/                     # HTTP security + routers
    security.py            # Imperative auth and Depends-wrapped helpers
    routers/
      admin.py             # Re-exports split admin routers
      admin_pkg/           # Admin routers split by domain
        api_keys.py        # /admin/api-keys, /admin/users
        tokens.py          # /admin/tokens
        apps.py            # /admin/apps
        groups.py          # /admin/groups (+ Casbin sync)
        policy.py          # /admin/policy/*
  repositories/            # DB helpers (e.g., casbin policies)
  schemas/                 # Pydantic schemas (Admin and MCP)
    admin.py               # Response/Request models for admin APIs
    mcp.py                 # ToolDef/Manifest and JSON-RPC models
  services/                # Domain services
    policy_sync.py         # Group→Casbin rules synchronization
  apikeys.py, apps.py, tokens.py, models.py, db.py, config.py, context.py

auth_helper/               # Wrapper package for vendor helper modules
  vendor/                  # Physically hosted helper modules (moved from auth-helper/)
  loader.py, cli.py, __main__.py, graph.py, tokens.py, dbsync.py, appreg.py, config.py

policy/
  model.conf               # Casbin model (RBAC + wildcards)
  policy.csv               # Default file policies (role:all, role:lite)

tests/
  curl_smoke.sh            # Basic server smoke
  policy_smoke.sh          # Per-user policy rule sanity
  default_policy_smoke.sh  # role:all default policy sanity
  groups_smoke.sh          # Default groups presence
  env.sample               # Test env template

alembic/versions/          # DB migrations (includes casbin_rule)

.env                       # Server env (do not commit secrets)
Makefile                   # The workflow entry point
README.md                  # Project overview and quickstart
```

--------------------------------------------------------------------------------

## 2) Environment & Configuration

Server `.env` (authoritative; typical keys)
- `PORT` (default 8081/8082 in examples)
- `ADMIN_API_KEY` (master key for /admin APIs)
- `DB_URL` (e.g., `sqlite:///./secrets/app.db`)
- `DB_AUTO_CREATE` (`true` to auto-create schema on boot; recommend `false` in prod)
- `CASBIN_MODEL=./policy/model.conf`
- File policy (simple): `CASBIN_POLICY=./policy/policy.csv`
- DB policy (recommended): `CASBIN_DB=true` (or `CASBIN_STORE=db`)
- Optional Graph defaults: `TENANT_ID`, `CLIENT_ID`, `SCOPES` (helper convenience)
- Tool schema dir (defaults to `./app/tools`): `TOOL_SCHEMA_DIR`

Test `.env` (`tests/.env`)
- `MCP_URL` (e.g., `http://localhost:8081`)
- `ADMIN_API_KEY` (admin smoke tests)

Strict policy: Never hardcode secrets or credentials in code or Make; inject via env only.

--------------------------------------------------------------------------------

## 3) Make First — Command Cheatsheet

Check current directory (required):
- `pwd` → ensure repo root.

Run local dev server:
- `make dev-serve`
  - Auto-load `.env`, start uvicorn, optional DB auto-create, seeds default groups.

Smoke tests:
- `make test`           # curl smoke (health, manifest, tools/list)
- `make test-defaults`  # default policy smoke (role:all)
- `make test-policy`    # per-user policy smoke
- `make test-groups`    # groups presence smoke

Admin helper flows (packaged wrapper):
- `make app-register ADMIN_PROFILE=admin [INTERACTIVE=1]`
- `make token-import PROFILE=alice FROM_FILE=./secrets/alice.json`
- `make user-add USER=alice TOKEN_PROFILE=alice TEMPLATE=lite`

Docker cleanups:
- `make docker-down-all`

Production (direct compose templates included):
- `make prod-up` / `make prod-down`

Note: If you add new flows, prefer creating dedicated Make targets encapsulating flags/env.

--------------------------------------------------------------------------------

## 4) Local Development Flow

1) Create/verify `.env` in repo root (copy from `.env.example` if needed).
2) `pwd` → must be repo root.
3) `source .venv/bin/activate` (Python 3.10–3.12), ensure dependencies are present.
4) `make dev-serve` to boot the API.
5) Use `make test*` targets for sanity.
6) For admin/Graph bootstrapping:
   - `python -m auth_helper.cli register-app --mcp-url http://localhost:$PORT --master-key $ADMIN_API_KEY --profile admin`
   - `python -m auth_helper.cli login --interactive --profile alice` to fetch a user token (if needed).

Rules of thumb
- Keep env-driven behavior; do not wire secrets inside code.
- When adding code, ensure pydantic response_models are defined (OpenAPI quality).
- Add/update Make targets when introducing new service flows.

--------------------------------------------------------------------------------

## 5) Authorization — Casbin (File or DB)

Model (policy/model.conf)
- RBAC via `g`, wildcards, and allow-only semantics.

Subjects considered (OR logic)
- `user_id`, `name`, `role`, `role:{role}`, `group:{group}`, `*`.

Objects
- Tool name, e.g., `todo.tasks.get`.

Actions
- `use` (uniform across tool visibility and execution).

Default policies (file)
- role:all → `p, role:all, *, use`
- role:lite → safe subset (lists, lite task ops, read-only sync)

Default seeding (DB)
- If `CASBIN_DB=true` and `casbin_rule` is empty at start, server auto-seeds role:all/lite policies.

Groups integration
- System seeds default groups: `admins`, `powerusers`, `readers` (idempotent).
- Group→policy sync writes `p, group:{name}, <tool>, use` rules on upsert/delete.

Operations
- List rules: `GET /admin/policy/rules`
- Add: `POST /admin/policy/rules`
- Delete: `DELETE /admin/policy/rules`
- Reload: `POST /admin/policy/reload`

--------------------------------------------------------------------------------

## 6) API Surface

MCP (JSON-RPC 2.0 over HTTP)
- `GET /mcp/manifest` → `ManifestResponse`
- `POST /mcp` → `JsonRpcEnvelope` (success or error). Body methods:
  - `initialize`
  - `tools/list`
  - `tools/call` (name + arguments)

Admin (master key required; split routers)
- API keys/users: `/admin/api-keys`, `/admin/users`
- Tokens: `/admin/tokens`
- Apps: `/admin/apps`
- Groups: `/admin/groups` (auto-sync to Casbin DB)
- Policy: `/admin/policy/*`

OpenAPI quality
- All admin endpoints specify `response_model`s (+ selected 4xx models).
- MCP endpoints expose typed response envelopes.

--------------------------------------------------------------------------------

## 7) Directory—By—Role Reference

- `app/tools.py`: Tool registration + execution. Tools are defined by JSON schemas in `app/tools/*.json`. When adding a tool:
  - Create a schema file with `name`, `description`, and `inputSchema`.
  - Provide an executor mapping via `_explicit_exec` or `_auto_exec`. Prefer conventional naming to be auto-bound.
  - Authorize it via Casbin (add p-lines or role policies).

- `app/auth/policy.py`: Do not copy this logic. Extend policies by adding Casbin rules (file or DB). Subject resolution and enforcement are centrally handled here.

- `app/api/routers/admin_pkg/*`: Add new admin domains here; assign `tags` and `dependencies=[Depends(dep_require_master)]`. Define request/response schemas in `app/schemas/admin.py`.

- `auth_helper/*`: Wrapper package providing `python -m auth_helper.cli`. Vendor modules are in `auth_helper/vendor/` and can be updated independently.

--------------------------------------------------------------------------------

## 8) Testing Strategy

Philosophy
- Keep tests self-contained and env-driven.
- Start narrow (modified code paths), expand to broader smoke runs as confidence grows.

Available smokes (bash)
- `tests/curl_smoke.sh` — health, manifest, tools/list
- `tests/policy_smoke.sh` — per-user policy allow-list sanity
- `tests/default_policy_smoke.sh` — default role:all policy sanity
- `tests/groups_smoke.sh` — default group presence

Run
- `cp tests/env.sample tests/.env` and edit values.
- `make test`, `make test-defaults`, `make test-policy`, `make test-groups` (server must be running).

--------------------------------------------------------------------------------

## 9) Production Notes

- Prefer DB-backed Casbin policies. Keep policy changes auditable and reload via admin API.
- Set `DB_AUTO_CREATE=false` in prod and run migrations with Alembic if needed.
- Place the server behind a reverse proxy (e.g., Traefik) and lock down `/admin/*` with strong master key handling and network ACLs.
- Keep secrets out of images. Inject via env or secret stores.
- Health check: `GET /health` (requires api or user key per config).

--------------------------------------------------------------------------------

## 10) Safe Operating Practices

- Always verify `pwd` and prefer `make` over ad-hoc commands.
- Use env files to isolate functions and environments (dev/stage/prod).
- Never commit `.env` or secrets.
- When extending APIs, add pydantic response models and examples.
- When touching authorization, think in Casbin policies (file or DB) — not in code conditionals.
- Keep bootstrap idempotent (seeding code must be safe to run multiple times).

--------------------------------------------------------------------------------

## 11) Troubleshooting (Common)

- 401/403 on `/mcp` or `/admin/*`:
  - Verify env has `ADMIN_API_KEY` (admin) or use user keys for MCP; confirm headers.
- Tools missing in `tools/list`:
  - Casbin policy denies them. Check file/db policies and group sync.
- NameError/Import issues around helper modules:
  - Use wrapper package `auth_helper` (`python -m auth_helper.cli`). Vendor modules are auto-loaded.
- DB policy doesn’t reflect group changes:
  - Ensure groups were upserted via admin API; server auto-syncs to casbin_rule.

--------------------------------------------------------------------------------

## 12) Glossary

- MCP: Model Context Protocol (JSON-RPC 2.0 interface for tools/list & tools/call)
- Casbin: Authorization engine; supports RBAC with DB/file adapters
- role:all / role:lite: Default policies
- group:<name>: Group subjects mapped to policies on demand
- Admin helper: Wrapper CLI at `auth_helper/` that drives app registration and token onboarding

--------------------------------------------------------------------------------

## 13) Final Notes for Agents

- Before you start: read `.env.example`, set `.env`, verify `pwd`, and run `make dev-serve`.
- Use Make. If you must run raw commands, mirror Make’s env flags.
- When adding features, update schemas, routers, policies, and tests in tandem.
- Be conservative with policy changes; prefer adding rules over code conditionals.
