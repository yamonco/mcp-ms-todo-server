Test suite for MCP HTTP server (manual/curl + Python).

Quick start
- Copy env sample: cp tests/env.sample tests/.env
- Edit tests/.env to set MCP_URL and ADMIN_API_KEY (for admin). For MCP calls, some tests create a user dynamically.
- Start server: make dev-serve (ensure CASBIN_MODEL is set; for DB policies also set CASBIN_DB=true)
- Run curl smoke: bash tests/curl_smoke.sh
- Run policy smoke (requires admin key and Casbin enabled): bash tests/policy_smoke.sh

What it checks
- /health reachable
- /mcp/manifest returns a tools array
- JSON-RPC initialize returns server/protocolRevision and NO OAuth fields
- tools/list returns tools array

Notes
- tools/call is not exercised by default because most tools require a valid Microsoft Graph token.
- You can add a call example after importing a DB token profile.
- With Casbin DB mode, ensure `POST /admin/policy/reload` is called after changing rules.
