
# License & Open Source Notice

This project is released under the MIT License by our organization. You are free to use, modify, distribute, and use it commercially. See the LICENSE file for details.


# MCP-MS-TODO-SERVER (2025 Latest MCP Structure)

This is an API server that integrates Microsoft To Do (Graph API) with MCP (Microsoft Cloud Platform). It is a FastAPI-based MCP server, and all features are provided via a single JSON-RPC endpoint (`/mcp`) using the tool system. You can quickly deploy and operate in a Docker environment, supporting Streamable HTTP (SSE), REST, and PowerShell (Microsoft.Graph) execution.

---


## Project Structure

```
- **Microsoft To Do (Graph API) Integration**: Supports authentication and CRUD operations
- **Streamable HTTP (SSE)**: Real-time progress log streaming
- **REST/PowerShell Execution**: REST by default, optional PowerShell (Microsoft.Graph)
- **Docker-based Deployment**: .env configuration, persistent token/log volumes

---

```bash
python -m app.cli users add \
    "time_zone": "Asia/Seoul"

# MCP-MS-TODO-SERVER (2025 Edition)

**A modern, production-grade MCP server for Microsoft To Do, built with FastAPI, Docker, and a strict argument-only automation flow.**

---

## Overview

This project provides a robust, secure, and extensible MCP (Model Context Protocol) server that integrates Microsoft To Do (via Microsoft Graph API) with a clean, tool-based JSON-RPC 2.0 interface. All automation, onboarding, and helper flows are strictly argument-based—**no environment variable dependencies**—for maximum portability, security, and CI/CD compatibility.

**Key Features:**
- Single `/mcp` JSON-RPC endpoint for all features (tools/list, tools/call)
- Microsoft To Do (Graph API) integration: CRUD, list, sync, etc.
- Argument-only CLI and onboarding: no env required, all helpers take explicit arguments
- Secure DB token storage, API key management, RBAC
- Docker-native, production-ready, with Makefile automation
- Real-time streaming (SSE), REST, and optional PowerShell execution
- Clean architecture: domain/usecases/infrastructure separation
- Optional Casbin authorization (file or DB policies)

### Module Layout (onboarding-friendly)

```
app/
  auth/                       # AuthN/Z boundary (Casbin)
    __init__.py               # re-exports (filter_tools_for, enforce_tool, reload)
    policy.py                 # Casbin wiring (file/DB, SSE-safe reload)
    adapter_sqlalchemy.py     # DB adapter (read-only)
  policy.py                   # legacy import shim to app.auth.policy
  casbin_adapter.py           # legacy import shim to app.auth.adapter_sqlalchemy
  apikeys.py                  # API key issuance (will be gradually moved to repositories/)
  models.py                   # SQLAlchemy models (includes casbin_rule)
  tools.py                    # Tool registry, validation, execution
  main.py                     # FastAPI JSON-RPC endpoint, admin endpoints
  ...
policy/
  model.conf                  # Casbin model (RBAC + wildcards)
  policy.csv                  # Sample file policy (optional)
```

This keeps existing imports stable while enabling a clean Auth module and full Casbin.

---

## Project Structure

```
mcp-ms-todo-server/
├── Dockerfile, docker-compose.yml      # Containerization & orchestration
├── README.md                          # This file
├── app/                               # Main server code (main.py, tools.py, domain/, usecases/, infrastructure/)
├── auth_helper/                      # CLI helper wrapper package (loads vendor'ed helper modules)
├── secrets/                           # Private tokens, DB, never committed
├── tools/                             # JSON schemas for tool definitions
├── tests/, docs/                      # Test scripts, Docusaurus docs
```

---

## Quick Start (Argument-Only, No Env)

1. **Build & Start (Docker):**
   ```bash
   docker compose build
   docker compose up -d
   ```

2. **Onboard & Register App (Argument-Only):**
   - Register Azure AD app (no env, all args):
     ```bash
     python -m auth_helper.cli register-app --mcp-url http://localhost:8081 --master-key <ADMIN_API_KEY> --admin-tenant-id <TENANT_ID> --admin-client-id <ADMIN_CLIENT_ID> --admin-client-secret <ADMIN_CLIENT_SECRET> --profile admin
     ```
   - Import user token (from stdin):
     ```bash
     echo '{"access_token":"..."}' | python -m app.cli profiles import --profile alice --from-stdin
     ```
   - Add user API key:
     ```bash
     python -m app.cli users add --user-id alice --name "Alice" --template lite --token-profile alice
     ```

3. **Run the Server:**
   ```bash
   make dev-serve
   # Or for production
   make prod-up
   ```

4. **Call Tools (JSON-RPC):**
   - List tools:
     ```json
     { "method": "tools/list", "params": {} }
     ```
   - Call a tool:
     ```json
     { "method": "tools/call", "params": { "name": "todo.tasks.get", "arguments": { "list_id": "<LIST_ID>" } } }
     ```

---

## Security & Best Practices

- **No environment variables required** for any helper, onboarding, or CLI flow. All secrets and config are passed as arguments.
- All tokens, API keys, and secrets are stored in the DB (`secrets/`), never committed.
- API access is protected by API keys (passed via `X-API-Key` header).
- RBAC and tool-level access control are enforced.
- `.env` and `secrets/` are gitignored by default.

### Casbin Authorization

This server can use Casbin to centrally control tool visibility and execution per user.

- Subject: prefers `user_id`, then `name`, then `role`, else `*`
- Object: tool name (e.g., `todo.tasks.get`)
- Action: `use`

Where it applies:
- tools/list: filtered by `app.policy.filter_tools_for()`
- tools/call: re-checked by `app.policy.enforce_tool()` (prevents bypass)
Note: DB `allowed_tools` is no longer enforced; Casbin is the single source of truth.

Configure (file-based):
```
CASBIN_MODEL=./policy/model.conf
CASBIN_POLICY=./policy/policy.csv
```

Configure (DB-based using table `casbin_rule`):
```
CASBIN_MODEL=./policy/model.conf
CASBIN_STORE=db  # or CASBIN_DB=true
```

Note: with DB-based policies, if the `casbin_rule` table is empty, all access is denied. Seed a baseline rule like `p, *, *, use` if you want allow-all during bootstrap.

Admin endpoint:
- `POST /admin/policy/reload` (master key required) to force reloading policies (needed for DB-backed updates)
- `GET /admin/policy/rules` to list current DB rules
- `POST /admin/policy/rules` to add a rule (ptype, v0..v5)
- `DELETE /admin/policy/rules` to delete matching rules (ptype, v0..v5)

### Migrating existing allowed_tools to Casbin (DB)

You can mirror current per-user tool permissions into `casbin_rule`:

Example SQL (SQLite) to grant each user_id access to their effective tools:

```sql
-- For each api key with user_id, insert p, <user_id>, <tool>, use
INSERT INTO casbin_rule (ptype, v0, v1, v2)
SELECT 'p' as ptype, ak.user_id as v0, akt.tool as v1, 'use' as v2
FROM api_keys ak
JOIN api_key_tools akt ON akt.key = ak.key
WHERE ak.user_id IS NOT NULL AND ak.user_id <> ''
;
```

If you use groups, insert additional rows for group-derived tools accordingly. After seeding, you can rely solely on Casbin.

### Recommended RBAC patterns

- Use role subjects prefixed (e.g., `role:admin`) in p-lines:
  - `p, role:admin, *, use` allows all tools for admins
- Map users to roles with g-lines in DB (`casbin_rule` with `ptype='g'`):
  - `g, alice, role:admin`
- Per-tool overrides (deny by omission): Casbin model allows only allow rules; omit p-lines to deny.


---

## Main API Usage Examples

### Get Task List
```json
{
  "method": "tools/call",
  "params": {
    "name": "todo.tasks.get",
    "arguments": {
      "list_id": "<LIST_ID>"
    }
  }
}
```

### Create Task
```json
{
  "tool": "todo.create_task",
  "params": {
    "list_id": "<LIST_ID>",
    "title": "Prepare meeting",
    "body": "Agenda summary",
    "due": "2025-09-05T09:00:00",
    "time_zone": "Asia/Seoul"
  }
}
```

---

## Supported Tools (as of 2025)

- `todo.lists.get`: List all To Do lists
- `todo.lists.mutate`: Create, delete, or rename a list
- `todo.tasks.get`: List all tasks in a list
- `todo.tasks.create`: Create a new task
- `todo.tasks.delete`: Delete a task

See `/tools/` for full JSON schemas and up-to-date tool definitions.

---

## Advanced: App Registration & Onboarding (No Env, Argument-Only)

All onboarding, app registration, and token import flows are **argument-only**. Example:

```bash
python -m auth_helper.cli register-app \
  --mcp-url http://localhost:8081 \
  --master-key <ADMIN_API_KEY> \
  --admin-tenant-id <TENANT_ID> \
  --admin-client-id <ADMIN_CLIENT_ID> \
  --admin-client-secret <ADMIN_CLIENT_SECRET> \
  --profile admin
```

Tokens can be imported from stdin or file, and all meta is upserted to the DB via the MCP API.

---

## Security Notes

- All secrets, tokens, and API keys are stored in the DB and never committed.
- `.env`, `secrets/`, and any DB files must be gitignored and kept private.
- Only delegated permissions are supported for Microsoft To Do (no application permissions).
- Periodic re-login may be required depending on your organization's security policy.

---

## Development & Contribution

- See `app/` for main server logic and tool definitions
- See `auth_helper/` for CLI wrapper; vendor helper modules are under `auth_helper/vendor/`
- See `tools/` for JSON schemas and tool documentation
- See `tests/` for smoke tests and usage examples
- See `docs/` for Docusaurus-based documentation

---

## License

MIT License. See LICENSE file for details.

---

## Contact & Feedback

For questions, issues, or feedback, please open an issue in this repository.
- `ADMIN_TENANT_ID`, `ADMIN_CLIENT_ID`, `ADMIN_CLIENT_SECRET`: Graph 앱 등록을 위한 관리자 앱 설정 (Application.ReadWrite.All 필요)
