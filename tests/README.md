Test suite for MCP HTTP server (manual/curl + Python).

Quick start
- Copy env sample: cp docker/mcp-ms-todo-server/tests/env.sample docker/mcp-ms-todo-server/tests/.env
- Edit .env to set MCP_URL and API_KEY
- Run curl smoke: bash docker/mcp-ms-todo-server/tests/curl_smoke.sh

What it checks
- /health reachable
- /mcp/manifest returns a tools array
- JSON-RPC initialize returns server/protocolRevision and NO OAuth fields
- tools/list returns tools array

Notes
- tools/call is not exercised by default because most tools require a valid Microsoft Graph token.
- You can add a call example after importing a DB token profile.
