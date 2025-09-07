---
sidebar_position: 3
---

# API Reference (2025 DB-first)

## JSON-RPC Endpoint
- `POST /mcp`
  - `tools/list`: Returns available tools (filtered by API key role/allowed_tools)
  - `tools/call`: Executes a tool with validated arguments

### Example (tools/call)
```json
{
  "method": "tools/call",
  "params": {
    "name": "todo.create_task",
    "arguments": {
      "list_id": "<LIST_ID>",
      "title": "Prepare meeting",
      "body": "Agenda",
      "due": "2025-12-01T09:00:00",
      "time_zone": "Asia/Seoul"
    }
  }
}
```

## Supported Tools (summary)
- `todo.lists.get`, `todo.lists.mutate`
- `todo.tasks.get`, `todo.tasks.create`, `todo.tasks.delete`, `todo.tasks.patch`
- `todo.tasks.lite_*`, `todo.sync.*` (if enabled)

Tool schemas are discoverable via `tools/list` (name + inputSchema provided).

## Admin Endpoints
- `GET /admin/api-keys`: List API keys
- `POST /admin/api-keys`: Create API key (template, role, token_profile/token_id, etc.)
- `PATCH /admin/api-keys/{key}`: Update key meta
- `DELETE /admin/api-keys/{key}`: Delete key

- `GET /admin/tokens`: List DB token profiles (summary)
- `GET /admin/tokens/by-profile/{profile}`: Read token (includes raw if present)
- `POST /admin/tokens`: Upsert token/meta for a profile

- `GET /admin/rbac/roles`: List RBAC roles
- `PUT /admin/rbac/roles/{name}`: Upsert role tools
- `DELETE /admin/rbac/roles/{name}`: Delete role

- `GET /admin/auth/status`: DB token presence summary
- `GET /metrics`: Prometheus metrics

Auth: Provide master key via `X-API-Key` for admin endpoints.

## Authentication Model (DB-only)
- No device-code flow. Tokens are provisioned/imported into DB `tokens` table.
- API keys reference tokens via `token_id` or `token_profile`.
