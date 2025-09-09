# Minimal Makefile (authentik-first)

.PHONY: help guard run dev-serve dev-clean dev-smoke mcp-tools mcp-call client-call \
        policy-reload docker-down-all prod-up prod-down authentik-up authentik-down authentik-reset \
        dev-up-bg dev-stop dev-status onboard-auth urls

# Port and base URL (prefer .dev.port runtime override if present)
PORT := $(shell awk -F= '/^PORT=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(PORT)),)
	PORT := 8081
endif
# Resolve MCP base URL
_MCP_DOMAIN := $(shell awk -F= '/^MCP_DOMAIN=/{print $$2}' .env 2>/dev/null | tail -n1)
_MCP_SCHEME := $(shell awk -F= '/^MCP_SCHEME=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(_MCP_SCHEME)),)
	_MCP_SCHEME := https
endif
ifeq ($(strip $(_MCP_DOMAIN)),)
	# no domain: fall back to localhost and dynamic dev port
	MCP_URL = $(shell if [ -f .dev.port ]; then printf 'http://localhost:%s' "$$(cat .dev.port)"; else printf 'http://localhost:%s' "$(PORT)"; fi)
else
	MCP_URL = $(_MCP_SCHEME)://$(_MCP_DOMAIN)
endif

# App prefix (for admin app register/reuse)
APP_PREFIX := $(shell awk -F= '/^APP_PREFIX=/{print $$2}' .env 2>/dev/null | tail -n1)

# Prefer uv
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(strip $(UV)),)
	RUN := python
else
	RUN := uv run --
endif

help:
	@echo "Targets: dev-serve, mcp-tools, mcp-call, policy-reload, authentik-up|down, prod-up|down"

urls:
	@bash -lc 'AD=$$(awk -F= "/^AUTH_DOMAIN=/{print $$2}" .env 2>/dev/null | tail -n1); \
	  if [ -n "$$AD" ]; then AK="https://$$AD"; else AK=$$(cat .auth.baseurl 2>/dev/null || echo http://localhost:$${AUTHENTIK_HTTP_PORT:-9190}); fi; \
	  if [ -n "$(_MCP_DOMAIN)" ]; then MU="$(MCP_URL)"; else MP=$$(if [ -f .dev.port ]; then cat .dev.port; else echo $(PORT); fi); MU="http://127.0.0.1:$$MP"; fi; \
	  echo "Authentik: $$AK"; echo "Authentik User: $$AK/if/user/"; echo "Authentik Admin: $$AK/if/admin/"; \
	  echo "MCP: $$MU"; echo "MCP capabilities: $$MU/mcp/capabilities"'

guard:
	@test -f pyproject.toml -a -d app || (pwd; echo "[ERR] Run from repo root" >&2; exit 1)

run: guard dev-serve

dev-serve: guard
	@if [ "$(CLEAN)" = "1" ]; then \
		$(MAKE) dev-clean; \
	fi
	@echo "[dev] free port $(PORT) if occupied"
	- docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans
	- pkill -f "uvicorn app.main:app" || true
	- bash -lc 'if command -v fuser >/dev/null 2>&1; then fuser -k $(PORT)/tcp || true; elif command -v lsof >/dev/null 2>&1; then PID=$$(lsof -ti tcp:$(PORT) || true); [ -n "$$PID" ] && kill -9 $$PID || true; fi'
	@echo "[dev] ensure authentik up (docker-compose.authentik.yml)"
	- $(MAKE) authentik-up
	@echo "[dev] choose available port"
	@bash -lc 'BASE=$(PORT); P=$$BASE; \
	  if command -v lsof >/dev/null 2>&1; then \
	    while lsof -i :$$P -sTCP:LISTEN >/dev/null 2>&1; do P=$$((P+1)); done; \
	  elif command -v fuser >/dev/null 2>&1; then \
	    while fuser $$P/tcp >/dev/null 2>&1; do P=$$((P+1)); done; \
	  fi; echo $$P > .dev.port; echo "[dev] using port $$P"'
	@echo "[dev] start FastAPI on port $$(cat .dev.port)"
	bash -lc 'set -a; [ -f .env ] && . ./.env; set +a; \
	  TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools}; PORT=$$(cat .dev.port); \
	  AKP=$$(cat .auth.port.http 2>/dev/null || echo $$AUTHENTIK_HTTP_PORT); \
	  export PORT AUTHENTIK_HTTP_PORT=$$AKP AUTHENTIK_BASE_URL="http://localhost:$$AKP" AUTHENTIK_INTROSPECTION_URL="http://localhost:$$AKP/application/o/introspect"; \
	  $(RUN) python -m uvicorn app.main:app --host 0.0.0.0 --port $$PORT --reload --reload-exclude "secrets/*"'

# Background dev with PID management
dev-up-bg: guard
	@if [ "$(CLEAN)" = "1" ]; then \
		$(MAKE) dev-clean; \
	fi
	@echo "[dev/bg] free port $(PORT) if occupied"
	- docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans
	- pkill -f "uvicorn app.main:app --host 0.0.0.0 --port $(PORT)" || true
	- bash -lc 'if command -v fuser >/dev/null 2>&1; then fuser -k $(PORT)/tcp || true; elif command -v lsof >/dev/null 2>&1; then PID=$$(lsof -ti tcp:$(PORT) || true); [ -n "$$PID" ] && kill -9 $$PID || true; fi'
	@echo "[dev/bg] ensure authentik up (docker-compose.authentik.yml)"
	- $(MAKE) authentik-up
	@echo "[dev/bg] choose available port"
	@bash -lc 'BASE=$(PORT); P=$$BASE; \
	  if command -v lsof >/dev/null 2>&1; then \
	    while lsof -i :$$P -sTCP:LISTEN >/dev/null 2>&1; do P=$$((P+1)); done; \
	  elif command -v fuser >/dev/null 2>&1; then \
	    while fuser $$P/tcp >/dev/null 2>&1; do P=$$((P+1)); done; \
	  fi; echo $$P > .dev.port; echo "[dev/bg] using port $$P"'
	@echo "[dev/bg] start FastAPI on port $$(cat .dev.port) in background"
	@bash -lc 'set -a; [ -f .env ] && . ./.env; set +a; \
	  TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools}; PORT=$$(cat .dev.port); \
	  AKP=$$(cat .auth.port.http 2>/dev/null || echo $$AUTHENTIK_HTTP_PORT); \
	  export PORT AUTHENTIK_HTTP_PORT=$$AKP AUTHENTIK_BASE_URL="http://localhost:$$AKP" AUTHENTIK_INTROSPECTION_URL="http://localhost:$$AKP/application/o/introspect"; \
	  nohup $(RUN) python -m uvicorn app.main:app --host 0.0.0.0 --port $$PORT --reload --reload-exclude "secrets/*" \
	    > server.log 2>&1 & echo $$! > .dev.pid; sleep 1; echo "PID: $$(cat .dev.pid 2>/dev/null || echo '-')"'

dev-stop: guard
	@echo "[dev/stop] stopping dev server (port $(PORT))"
	- bash -lc 'if [ -f .dev.pid ]; then PID=$$(cat .dev.pid); kill $$PID 2>/dev/null || true; sleep 1; rm -f .dev.pid; fi'
	- pkill -f "uvicorn app.main:app --host 0.0.0.0 --port $(PORT)" || true
	- bash -lc 'if command -v fuser >/dev/null 2>&1; then fuser -k $(PORT)/tcp || true; elif command -v lsof >/dev/null 2>&1; then PID=$$(lsof -ti tcp:$(PORT) || true); [ -n "$$PID" ] && kill -9 $$PID || true; fi'
	@echo "[dev/stop] done"

dev-status:
	@bash -lc 'if [ -f .dev.pid ]; then echo "PID file: $$(cat .dev.pid)"; else echo "No PID file"; fi; \
	  P=$$(cat .dev.port 2>/dev/null || echo $(PORT)); echo "PORT: $$P"; \
	  if command -v lsof >/dev/null 2>&1; then lsof -nP -i :$$P || true; else echo "Install lsof for detailed status"; fi'

dev-clean: guard
	@echo "[clean] shutting down dev containers and removing volumes"
	- docker compose -f docker-compose.authentik.yml down -v --remove-orphans
	- docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans
	@echo "[clean] removing local SQLite DBs in secrets/"
	- rm -f secrets/*.db 2>/dev/null || true
	@echo "[clean] done"

dev-smoke: guard
	@echo "[dev] smoke tests"
	TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
		DB_URL=$${DB_URL:-sqlite:///./secrets/test.db} DB_AUTO_CREATE=true \
		$(RUN) python smoke_test.py

# JSON-RPC helpers (use Authorization: Bearer)
BEARER_TOKEN ?=
PARAMS ?= {}
mcp-tools:
	curl -sS $(MCP_URL)/mcp -H 'Content-Type: application/json' \
	  -H "Authorization: Bearer ${BEARER_TOKEN}" \
	  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .

mcp-call:
	curl -sS $(MCP_URL)/mcp -H 'Content-Type: application/json' \
	  -H "Authorization: Bearer ${BEARER_TOKEN}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .

# X-API-Key variants
USER_API_KEY ?=
mcp-tools-key:
	curl -sS $(MCP_URL)/mcp -H 'Content-Type: application/json' \
	  -H "X-API-Key: ${USER_API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .

mcp-call-key:
	curl -sS $(MCP_URL)/mcp -H 'Content-Type: application/json' \
	  -H "X-API-Key: ${USER_API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .

client-call:
	@BEARER_TOKEN=$(BEARER_TOKEN) npx -y node client/mcp-client.mjs --url $(MCP_URL) --key $(BEARER_TOKEN) --method $(METHOD) --params '$(PARAMS)'

# Ops
policy-reload: guard
	MCP_URL=$(MCP_URL) $(RUN) python -m app.admin_cli policy-reload | jq .

# ---------------------------
# Onboarding helpers (Make UX)
# Requires: AUTHENTIK_TOKEN in env for admin endpoints
# ---------------------------

ensure-secrets-dir:
	@mkdir -p secrets

auth-check:
	@echo "[auth] checking admin access via /ops/policy/reload"
	MCP_URL=$(MCP_URL) $(RUN) python -m app.admin_cli policy-reload | jq .

admin-app:
	@[ -n "$(APP_PREFIX)" ] || (echo "APP_PREFIX is not set in .env" >&2; exit 1)
	@bash -lc 'H=( -H "content-type: application/json" ); \
	  [ -n "$$AUTHENTIK_TOKEN" ] && H+=(-H "Authorization: Bearer $$AUTHENTIK_TOKEN"); \
	  [ -n "$$ADMIN_API_KEY" ] && H+=(-H "X-API-Key: $$ADMIN_API_KEY"); \
	  curl -sS -X POST $(MCP_URL)/admin/apps/register_or_reuse "$${H[@]}" \
	    -d '{"app_prefix":"$(APP_PREFIX)"}' | tee secrets/last_app.json'

# Usage: make token-upsert PROFILE=alice TOKEN_JSON=token.json TENANT_ID=... CLIENT_ID=... CLIENT_SECRET=... TOKEN_ENDPOINT=...
token-upsert: ensure-secrets-dir
	@[ -n "$(PROFILE)" ] || (echo "PROFILE is required" >&2; exit 1)
	@bash -lc 'H=( -H "content-type: application/json" ); \
	  [ -n "$$AUTHENTIK_TOKEN" ] && H+=(-H "Authorization: Bearer $$AUTHENTIK_TOKEN"); \
	  [ -n "$$ADMIN_API_KEY" ] && H+=(-H "X-API-Key: $$ADMIN_API_KEY"); \
	  TJ="$(TOKEN_JSON)"; [ -z "$${TJ}" -a -f secrets/token.json ] && TJ=secrets/token.json; \
	  if [ -n "$${TJ}" ]; then \
	    jq --arg profile "$(PROFILE)" --arg tenant_id "$(TENANT_ID)" --arg client_id "$(CLIENT_ID)" \
	       --arg client_secret "$(CLIENT_SECRET)" --arg token_endpoint "$(TOKEN_ENDPOINT)" \
	       --argjson app_id ${APP_ID:-null} \
	       '. + {profile:$profile, tenant_id:$tenant_id, client_id:$client_id, client_secret:$client_secret, token_endpoint:$token_endpoint, app_id:$app_id}' \
	       "$${TJ}" \
	      | curl -sS -X POST $(MCP_URL)/admin/tokens "$${H[@]}" -d @- | tee secrets/last_token.json; \
	  else \
	    curl -sS -X POST $(MCP_URL)/admin/tokens "$${H[@]}" \
	      -d '{"profile":"$(PROFILE)","tenant_id":"$(TENANT_ID)","client_id":"$(CLIENT_ID)","client_secret":"$(CLIENT_SECRET)","token_endpoint":"$(TOKEN_ENDPOINT)","app_id":$(APP_ID)}' \
	      | tee secrets/last_token.json; \
	  fi'

# Usage: make apikey-add USER_ID=alice ROLE=role:lite PROFILE=alice
apikey-add: ensure-secrets-dir
	@[ -n "$(USER_ID)" ] || (echo "USER_ID is required" >&2; exit 1)
	@[ -n "$(ROLE)" ] || (echo "ROLE is required (e.g., role:lite)" >&2; exit 1)
	@[ -n "$(PROFILE)" ] || (echo "PROFILE is required (token profile)" >&2; exit 1)
	@bash -lc 'H=( -H "content-type: application/json" ); \
	  [ -n "$$AUTHENTIK_TOKEN" ] && H+=(-H "Authorization: Bearer $$AUTHENTIK_TOKEN"); \
	  [ -n "$$ADMIN_API_KEY" ] && H+=(-H "X-API-Key: $$ADMIN_API_KEY"); \
	  curl -sS -X POST $(MCP_URL)/admin/api-keys "$${H[@]}" \
	    -d '{"user_id":"$(USER_ID)","name":"$(NAME)","role":"$(ROLE)","token_profile":"$(PROFILE)","app_id":$(APP_ID)}' \
	    | tee secrets/last_apikey.json; \
	  jq -r .key secrets/last_apikey.json > secrets/last_user_key 2>/dev/null || true; \
	  echo "Saved last API key to secrets/last_user_key"'

# Pull tokens from current Authentik admin bearer claims
# Usage: make token-from-auth PROFILE=alice [APP_ID=1]
token-from-auth: ensure-secrets-dir
	@[ -n "$(PROFILE)" ] || (echo "PROFILE is required" >&2; exit 1)
	@bash -lc 'H=( -H "content-type: application/json" ); \
	  [ -n "$$AUTHENTIK_TOKEN" ] && H+=(-H "Authorization: Bearer $$AUTHENTIK_TOKEN"); \
	  [ -n "$$ADMIN_API_KEY" ] && H+=(-H "X-API-Key: $$ADMIN_API_KEY"); \
	  curl -sS -X POST $(MCP_URL)/admin/tokens/from_auth "$${H[@]}" \
	    -d '{"profile":"$(PROFILE)","app_id":$(APP_ID)}' | tee secrets/last_token.json'

# One-shot onboarding: app -> token -> apikey
# Example:
#   make onboard PROFILE=alice USER_ID=alice ROLE=role:lite TOKEN_JSON=token.json
onboard: admin-app
	@bash -lc 'if [ -n "$(TENANT_ID)$(CLIENT_ID)$(CLIENT_SECRET)$(TOKEN_ENDPOINT)$(TOKEN_JSON)" ]; then \
	  $(MAKE) token-upsert PROFILE=$(PROFILE) TENANT_ID=$(TENANT_ID) CLIENT_ID=$(CLIENT_ID) CLIENT_SECRET=$(CLIENT_SECRET) TOKEN_ENDPOINT=$(TOKEN_ENDPOINT) TOKEN_JSON=$(TOKEN_JSON) APP_ID=$(APP_ID); \
	else \
	  $(MAKE) token-from-auth PROFILE=$(PROFILE) APP_ID=$(APP_ID); \
	fi'
	$(MAKE) apikey-add USER_ID=$(USER_ID) ROLE=$(ROLE) PROFILE=$(PROFILE) APP_ID=$(APP_ID)

# Onboard via Authentik-only flow (no env Graph creds)
onboard-auth: admin-app token-from-auth apikey-add
	@echo "[onboard] Done. USER_API_KEY: $$(cat secrets/last_user_key 2>/dev/null || echo '<none>')"

# Docker
authentik-up: guard
	@bash -lc 'HP="$$AUTHENTIK_HTTP_PORT"; SP="$$AUTHENTIK_HTTPS_PORT"; \
	  [ -z "$$HP" ] && HP=9190; [ -z "$$SP" ] && SP=9444; \
	  if command -v lsof >/dev/null 2>&1; then \
	    while lsof -i :$$HP -sTCP:LISTEN >/dev/null 2>&1; do HP=$$((HP+1)); done; \
	    while lsof -i :$$SP -sTCP:LISTEN >/dev/null 2>&1; do SP=$$((SP+1)); done; \
	  elif command -v fuser >/dev/null 2>&1; then \
	    while fuser $$HP/tcp >/dev/null 2>&1; do HP=$$((HP+1)); done; \
	    while fuser $$SP/tcp >/dev/null 2>&1; do SP=$$((SP+1)); done; \
	  fi; \
	  echo $$HP > .auth.port.http; echo $$SP > .auth.port.https; \
	  echo "http://localhost:$$HP" > .auth.baseurl; \
	  echo "[authentik] using ports http=$$HP https=$$SP"; \
	  AUTHENTIK_HTTP_PORT=$$HP AUTHENTIK_HTTPS_PORT=$$SP \
	    docker compose -p mcp-authentik -f docker-compose.authentik.yml up -d'

authentik-down: guard
	docker compose -p mcp-authentik -f docker-compose.authentik.yml down --remove-orphans

authentik-reset: guard
	docker compose -p mcp-authentik -f docker-compose.authentik.yml down -v --remove-orphans

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env up -d

prod-up-proxy:
	docker compose -f docker-compose.yml -f docker-compose.traefik.yml --env-file .env up -d

prod-down-proxy:
	docker compose -f docker-compose.yml -f docker-compose.traefik.yml --env-file .env down --remove-orphans

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans

docker-down-all: guard
	-docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans
	-docker compose -f docker-compose-tool.yml --env-file .env down --remove-orphans
	-docker compose -f docker-compose.traefik.yml --env-file .env down --remove-orphans

# Authentik behind Traefik (prod)
auth-prod-up-proxy:
	docker compose -p mcp-authentik -f docker-compose.authentik.yml -f docker-compose.authentik.traefik.yml --env-file .env up -d

auth-prod-down-proxy:
	docker compose -p mcp-authentik -f docker-compose.authentik.yml -f docker-compose.authentik.traefik.yml --env-file .env down --remove-orphans
