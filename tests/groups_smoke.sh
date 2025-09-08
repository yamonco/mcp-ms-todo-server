#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
[ -f "$DIR/.env" ] && source "$DIR/.env"

MCP_URL=${MCP_URL:-http://localhost:8081}
ADMIN_API_KEY=${ADMIN_API_KEY:-}

if [ -z "$ADMIN_API_KEY" ]; then
  echo "[skip] ADMIN_API_KEY not set; groups smoke requires admin access" >&2
  exit 0
fi

RES=$(curl -sS "$MCP_URL/admin/groups" -H "x-api-key: $ADMIN_API_KEY")
echo "$RES" | jq .
echo "$RES" | jq -e 'has("admins")' >/dev/null || { echo "[fail] admins group missing" >&2; exit 1; }
echo "[ok] groups smoke passed (admins present)"

