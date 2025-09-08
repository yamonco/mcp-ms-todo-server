#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
[ -f "$DIR/.env" ] && source "$DIR/.env"

MCP_URL=${MCP_URL:-http://localhost:8081}
ADMIN_API_KEY=${ADMIN_API_KEY:-}

if [ -z "$ADMIN_API_KEY" ]; then
  echo "[skip] ADMIN_API_KEY not set; policy smoke requires admin access" >&2
  exit 0
fi

u_id=${TEST_USER_ID:-casbin_tester}

echo "[policy] create API key for user_id=$u_id (template=lite)"
CREATE_RES=$(curl -sS -X POST "$MCP_URL/admin/users" \
  -H 'content-type: application/json' \
  -H "x-api-key: $ADMIN_API_KEY" \
  -d "{\"template\":\"lite\",\"user_id\":\"$u_id\",\"name\":\"$u_id\"}")
echo "$CREATE_RES" | jq . >/dev/null
USER_KEY=$(echo "$CREATE_RES" | jq -r '.api_key')
if [ -z "$USER_KEY" ] || [ "$USER_KEY" = null ]; then
  echo "[fail] could not create api key" >&2
  echo "$CREATE_RES" >&2
  exit 1
fi
echo "[policy] user API key: $USER_KEY"

echo "[policy] add allow rule: p, $u_id, todo.lists.get, use"
curl -sS -X POST "$MCP_URL/admin/policy/rules" \
  -H 'content-type: application/json' -H "x-api-key: $ADMIN_API_KEY" \
  -d '{"ptype":"p","v0":"'"$u_id"'","v1":"todo.lists.get","v2":"use"}' | jq .

echo "[policy] reload"
curl -sS -X POST "$MCP_URL/admin/policy/reload" -H "x-api-key: $ADMIN_API_KEY" | jq .

echo "[policy] tools/list with user key"
TL_PAY='{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }'
RES=$(curl -sS "$MCP_URL/mcp" -H 'content-type: application/json' -H "x-api-key: $USER_KEY" -d "$TL_PAY")
echo "$RES" | jq .
COUNT=$(echo "$RES" | jq '.result.tools | length')
NAME0=$(echo "$RES" | jq -r '.result.tools[0].name // empty')
if [ "$COUNT" -lt 1 ] || [ "$NAME0" != "todo.lists.get" ]; then
  echo "[fail] expected only todo.lists.get, got: COUNT=$COUNT NAME0=$NAME0" >&2
  exit 1
fi
echo "[ok] policy smoke passed"

