#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
if [ -f "$DIR/.env" ]; then
  # shellcheck disable=SC1091
  source "$DIR/.env"
fi

# MCP_URL은 .env에서 읽지 않고 PORT만 사용
PORT=${PORT:-8081}
MCP_URL="http://localhost:${PORT}"
ADMIN_API_KEY=${ADMIN_API_KEY:-}
USER_API_KEY=${USER_API_KEY:-}

echo "[info] MCP_URL=$MCP_URL"
if [ -z "$ADMIN_API_KEY" ]; then
  echo "[warn] ADMIN_API_KEY is empty; admin endpoints may fail"
fi
if [ -z "$USER_API_KEY" ]; then
  echo "[warn] USER_API_KEY is empty; MCP calls may fail (dev-open only)"
fi

curl_json() {
  local path=$1
  shift || true
  curl -sS "$MCP_URL$path" "$@" | jq .
}

echo "[1] GET /health"
curl_json "/health"

echo "[2] GET /mcp/manifest (with user key if provided)"
if [ -n "$USER_API_KEY" ]; then
  curl -sS "$MCP_URL/mcp/manifest" -H "x-api-key: $USER_API_KEY" | jq .
else
  curl -sS "$MCP_URL/mcp/manifest" | jq .
fi

echo "[3] POST /mcp initialize"
INIT_PAY='{ "jsonrpc": "2.0", "id": 1, "method": "initialize" }'
if [ -n "$USER_API_KEY" ]; then AUTH=(-H "x-api-key: $USER_API_KEY"); else AUTH=(); fi
INIT_RES=$(curl -sS "$MCP_URL/mcp" -H 'content-type: application/json' "${AUTH[@]}" -d "$INIT_PAY")
echo "$INIT_RES" | jq .

echo "[3a] Assert initialize result contains server + protocolRevision"
echo "$INIT_RES" | jq -e '.result.server.name and .result.protocolRevision' >/dev/null

echo "[3b] Assert initialize does NOT declare OAuth fields"
# Fail if any of these fields appear anywhere in result
if echo "$INIT_RES" | jq -e '(.result | tostring) | test("authorizationUrl|tokenUrl|clientId|scopes|oauth"; "i")' >/dev/null; then
  echo "[FAIL] initialize result appears to declare OAuth-related fields" >&2
  exit 1
fi
echo "[ok] initialize has no OAuth hints"

echo "[4] POST /mcp tools/list"
TL_PAY='{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }'
curl -sS "$MCP_URL/mcp" -H 'content-type: application/json' "${AUTH[@]}" -d "$TL_PAY" | jq .

echo "[done] curl smoke completed"
