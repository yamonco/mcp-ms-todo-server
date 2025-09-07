#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
if [ -f "$DIR/.env" ]; then
  # shellcheck disable=SC1091
  source "$DIR/.env"
fi

MCP_URL=${MCP_URL:-http://localhost:8081}
API_KEY=${API_KEY:-}

echo "[info] MCP_URL=$MCP_URL"
if [ -z "$API_KEY" ]; then
  echo "[warn] API_KEY is empty; endpoints requiring key may fail"
fi

curl_json() {
  local path=$1
  shift || true
  curl -sS "$MCP_URL$path" "$@" | jq .
}

echo "[1] GET /health"
curl_json "/health"

echo "[2] GET /mcp/manifest (with key if provided)"
if [ -n "$API_KEY" ]; then
  curl -sS "$MCP_URL/mcp/manifest" -H "x-api-key: $API_KEY" | jq .
else
  curl -sS "$MCP_URL/mcp/manifest" | jq .
fi

echo "[3] POST /mcp initialize"
INIT_PAY='{ "jsonrpc": "2.0", "id": 1, "method": "initialize" }'
if [ -n "$API_KEY" ]; then AUTH=(-H "x-api-key: $API_KEY"); else AUTH=(); fi
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
