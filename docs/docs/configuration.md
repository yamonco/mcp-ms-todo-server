---
sidebar_position: 5
---

# Configuration (2025)

All settings are environment variables. No JSON token files are used.

## Server
- `SERVER_NAME` (default: MCP To Do Server)
- `SERVER_VERSION` (default: 0.2.0)
- `MCP_PROTOCOL_REV` (default: 2025-06-18)
- `PORT` (default: 8081)
- `LOG_LEVEL` (default: INFO)
- `API_KEY` (master key; required for admin endpoints)
- `SSE_ENABLED` (default: true)
- `ALLOW_ORIGINS` (comma separated)

## Database
- `DB_URL` (e.g., `sqlite:///./secrets/app.db`)
- `DB_ECHO` (default: false)
- `DB_AUTO_CREATE` (default: true; dev only)

## Microsoft Graph / Auth Helper
- `ADMIN_TENANT_ID` (for app-register)
- `ADMIN_CLIENT_ID`, `ADMIN_CLIENT_SECRET` (Application.ReadWrite.All)
- `APP_PREFIX` (default: mcp-todo-server)
- `SCOPES` (default: `Tasks.ReadWrite offline_access`)

## Tool Schema
- `TOOL_SCHEMA_DIR` (default: app/tools)
