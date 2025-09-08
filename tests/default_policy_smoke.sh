#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
[ -f "$DIR/.env" ] && source "$DIR/.env"

MCP_URL=${MCP_URL:-http://localhost:8081}
ADMIN_API_KEY=${ADMIN_API_KEY:-}

if [ -z "$ADMIN_API_KEY" ]; then
  echo "[skip] ADMIN_API_KEY not set; default policy smoke requires admin access" >&2
  exit 0
fi

u_id=${TEST_USER_ID_ALL:-casbin_admin}

echo "[default-policy] create API key for user_id=$u_id (template=all)"
CREATE_RES=$(curl -sS -X POST "$MCP_URL/admin/users" \
  -H 'content-type: application/json' \
  -H "x-api-key: $ADMIN_API_KEY" \
  -d "{\"template\":\"all\",\"user_id\":\"$u_id\",\"name\":\"$u_id\"}")
echo "$CREATE_RES" | jq . >/dev/null
USER_KEY=$(echo "$CREATE_RES" | jq -r '.api_key')
if [ -z "$USER_KEY" ] || [ "$USER_KEY" = null ]; then
  echo "[fail] could not create api key" >&2
  echo "$CREATE_RES" >&2
  exit 1
fi
echo "[default-policy] user API key: $USER_KEY"

echo "[default-policy] tools/list should include multiple tools (role:all has * access)"
TL_PAY='{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }'
RES=$(curl -sS "$MCP_URL/mcp" -H 'content-type: application/json' -H "x-api-key: $USER_KEY" -d "$TL_PAY")
echo "$RES" | jq .
COUNT=$(echo "$RES" | jq '.result.tools | length')
if [ "$COUNT" -lt 3 ]; then
  echo "[fail] expected several tools for role:all; got COUNT=$COUNT" >&2
  exit 1
fi
echo "[ok] default policy smoke passed"

