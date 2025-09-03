---
sidebar_position: 5
---

# Configuration

All settings are read from environment variables via `app/config.py`.

Server:
- `SERVER_NAME` (default: MCP To Do Server)
- `SERVER_VERSION` (default: 0.2.0)
- `MCP_PROTOCOL_REV` (default: 2025-06-18)
- `PORT` (default: 8081)
- `LOG_LEVEL` (default: INFO)
- `API_KEY` (optional; when set, required for requests)
- `SSE_ENABLED` (default: true)
- `ALLOW_ORIGINS` (comma separated)

Paths:
- `MCP_TOKEN_FILE` or `TOKEN_PATH` (default: /app/secrets/token.json)
- `TOOL_SCHEMA_DIR` (default: app/tools)

HTTP/Graph:
- `GRAPH_BASE_URL` (default: https://graph.microsoft.com/v1.0)
- `HTTP_TIMEOUT` (default: 30)
- `HTTP_MAX_RETRIES` (default: 2)
- `HTTP_BACKOFF_INITIAL` (default: 0.8)
- `HTTP_BACKOFF_FACTOR` (default: 2.0)

Rate limit & Circuit breaker:
- `RATE_PER_SEC` (default: 5)
- `RATE_BURST` (default: 5)
- `CB_FAILS` (default: 3)
- `CB_COOLDOWN_SEC` (default: 5)

