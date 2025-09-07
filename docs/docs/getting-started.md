---
sidebar_position: 2
---

# Getting Started (Make + CLI)

## Prerequisites
- Docker (recommended) or local Python (uv/uvicorn)
- SQLite (default) or external DB for `DB_URL`

## Quick Setup
```bash
cp .env.example .env
make db-up                 # Alembic migrations
make app-register PROFILE=admin   # Register/reuse app via Graph, save meta to DB

# Import a user's token JSON into DB (replace with real values)
echo '{"access_token":"...","refresh_token":"...","expires_on":1736200000}' \
  | make token-import PROFILE=alice TOKEN='@-'

# Create user API key mapped to the token profile
make user-add USER=alice NAME="Alice" TEMPLATE=lite TOKEN_PROFILE=alice

# Start server (dev)
make dev-serve
```

## One‑Shot Onboarding
```bash
make onboard-user USER=alice NAME="Alice" FROM_FILE=./secrets/alice.json
```

## Call Tools
- List tools: `make mcp-tools API_KEY=<user_api_key>`
- Call tool: `make mcp-call API_KEY=<user_api_key> METHOD=tools/call PARAMS='{"name":"todo.lists.get","arguments":{}}'`
