
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

---

## Project Structure

```
mcp-ms-todo-server/
├── Dockerfile, docker-compose.yml      # Containerization & orchestration
├── README.md                          # This file
├── app/                               # Main server code (main.py, tools.py, domain/, usecases/, infrastructure/)
├── auth-helper/                       # CLI helper for app registration, onboarding, token import (argument-only)
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
     python auth-helper/auth-helper.py register-app --mcp-url http://localhost:8081 --master-key <API_KEY> --admin-tenant-id <TENANT_ID> --admin-client-id <ADMIN_CLIENT_ID> --admin-client-secret <ADMIN_CLIENT_SECRET> --profile admin
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
python auth-helper/auth-helper.py register-app \
  --mcp-url http://localhost:8081 \
  --master-key <API_KEY> \
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
- See `auth-helper/` for argument-only onboarding and app registration helpers
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
