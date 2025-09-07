.PHONY: help dev-serve dev-smoke mcp-tools mcp-call docker-down-all \
        db-up app-register token-import user-add auth-init auth-refresh auth-status \
        onboard-user prod-up prod-down

# .env 에서 PORT 파싱 (없으면 8081)
PORT := $(shell awk -F= '/^PORT=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(PORT)),)
  PORT := 8081
endif
MCP_URL = http://localhost:$(PORT)

# Compose 파일 경로(정리용)
COMPOSE_TOOL    = docker compose -f docker-compose-tool.yml --env-file .env
COMPOSE_ROOT    = docker compose -f docker-compose.yml   --env-file .env
COMPOSE_DIRECT  = docker compose -f docker-compose.yml -f docker-compose.direct.yml   --env-file .env
COMPOSE_TRAEFIK = docker compose -f docker-compose.yml -f docker-compose.traefik.yml  --env-file .env

help:
	@echo "Targets:"
	@echo "  dev-serve       : Start FastAPI locally (uv, foreground)"
	@echo "  dev-smoke       : Run local smoke tests with uv"
	@echo "  mcp-tools       : Call tools/list against local server"
	@echo "  mcp-call        : Call arbitrary method via JSON-RPC"
	@echo "  docker-down-all : Stop all compose stacks (server/tool/direct/traefik)"
	@echo "  db-up           : Run Alembic migrations (upgrade head)"
	@echo "  app-register    : Register/reuse app via Graph and save meta to DB"
	@echo "  token-import    : Import raw token JSON into DB profile"
	@echo "  user-add        : Create API key for a user and attach DB token"
	@echo "  auth-init       : Validate/refresh token via helper (DB)"
	@echo "  auth-refresh    : Force refresh via helper (DB)"
	@echo "  auth-status     : Show helper token status (DB)"
	@echo "  onboard-user    : One-shot: token import + user add (USER, NAME env)"
	@echo "  prod-up         : Start server via docker compose (direct)"
	@echo "  prod-down       : Stop server via docker compose (direct)"
	@echo "Env: MCP_URL, API_KEY, ADMIN_* for app-register; PROFILE, FROM_FILE or TOKEN for token-import"

# ---------- Local development (uv) ----------

dev-serve:
	@echo "[dev] Loading .env and starting FastAPI (foreground) on port $(PORT)"
	bash -lc 'set -a; [ -f .env ] && . ./.env; set +a; \
	  TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
	  uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload --reload-exclude "secrets/*"'


dev-smoke:
	@echo "[dev] Running smoke tests locally"
	API_KEY=$${API_KEY:-test-key} TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
	DB_URL=$${DB_URL:-sqlite:///./secrets/test.db} DB_AUTO_CREATE=true \
	uv run python smoke_test.py

# ---------- JSON-RPC helpers ----------

mcp-tools:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .

PARAMS ?= {}
mcp-call:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .

# ---------- Docker cleanup ----------

docker-down-all:
	-$(COMPOSE_DIRECT) down --remove-orphans
	-$(COMPOSE_TRAEFIK) down --remove-orphans
	-$(COMPOSE_ROOT) down --remove-orphans
	-$(COMPOSE_TOOL) down --remove-orphans

# ---------- DB & Auth Helper UX ----------

db-up:
	@echo "[db] alembic upgrade head"
	uv run alembic upgrade head

# Usage: make app-register PROFILE=admin [INTERACTIVE=1]
PROFILE ?= admin
INTERACTIVE ?=
app-register:
	@test -n "$$API_KEY" || (echo "API_KEY is required in env (.env)." && false)
	@test -n "$$ADMIN_TENANT_ID" || (echo "ADMIN_TENANT_ID required." && false)
	@if [ -n "$(INTERACTIVE)" ]; then \
	  TOKEN_PROFILE=$(PROFILE) uv run python auth-helper/auth-helper.py register-app --interactive; \
	else \
	  TOKEN_PROFILE=$(PROFILE) uv run python auth-helper/auth-helper.py register-app; \
	fi

# Usage: make token-import PROFILE=alice FROM_FILE=./secrets/alice.json
#   or:  make token-import PROFILE=alice TOKEN='{"access_token":"..."}'
TOKEN ?=
FROM_FILE ?=
token-import:
	@test -n "$(PROFILE)" || (echo "PROFILE required (ex: PROFILE=alice)" && false)
	@if [ -z "$(TOKEN)" ] && [ -n "$(FROM_FILE)" ]; then \
	  TOKEN="$$(cat $(FROM_FILE))"; \
	fi; \
	[ -n "$$TOKEN" ] || (echo "Provide TOKEN='json' or FROM_FILE=path" && false); \
	MCP_URL=$(MCP_URL) uv run python -m app.cli profiles import --profile $(PROFILE) --token "$$TOKEN"

# Usage: make user-add USER=alice NAME="Alice" [TEMPLATE=lite] [TOKEN_ID=1|TOKEN_PROFILE=alice]
TOKEN_ID ?=
TOKEN_PROFILE ?=
user-add:
	@test -n "$(USER)" || (echo "USER required (ex: USER=alice)" && false)
	@if [ -z "$(TOKEN_ID)" ] && [ -z "$(TOKEN_PROFILE)" ]; then \
	  echo "Provide TOKEN_ID or TOKEN_PROFILE" && false; \
	fi; \
	MCP_URL=$(MCP_URL) uv run python -m app.cli users add \
	  --user-id "$(USER)" \
	  $(if $(NAME),--name "$(NAME)",) \
	  --template "$(if $(TEMPLATE),$(TEMPLATE),lite)" \
	  $(if $(TOKEN_ID),--token-id "$(TOKEN_ID)",) \
	  $(if $(TOKEN_PROFILE),--token-profile "$(TOKEN_PROFILE)",)

auth-init:
	uv run python auth-helper/auth-helper.py init

auth-refresh:
	uv run python auth-helper/auth-helper.py refresh --slack-seconds 0

auth-status:
	uv run python auth-helper/auth-helper.py status

# ---------- One-shot onboarding ----------

# Usage: make onboard-user USER=alice NAME="Alice" [AUTH_MODE=local|docker|az] [STORE=per-user|shared]
# Optional: TEMPLATE (default: USER_TEMPLATE_DEFAULT or 'lite')
AUTH_MODE ?= local
STORE ?= per-user
TEMPLATE ?=
FROM_FILE ?=

onboard-user:
	@test -n "$(USER)" || (echo "USER is required. ex) make onboard-user USER=alice NAME=Alice" && false)
	@test -n "$(FROM_FILE)$(TOKEN)" || (echo "Provide FROM_FILE=path or TOKEN='json'" && false)
	$(MAKE) token-import PROFILE=$(USER) FROM_FILE="$(FROM_FILE)" TOKEN='$(TOKEN)'
	$(MAKE) user-add USER=$(USER) NAME='$(NAME)' TEMPLATE='$(TEMPLATE)' TOKEN_PROFILE=$(USER)

# ---------- Production (docker compose, direct) ----------

prod-up:
	$(COMPOSE_DIRECT) up -d

prod-down:
	$(COMPOSE_DIRECT) down --remove-orphans
