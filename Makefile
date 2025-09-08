# Make targets are thin wrappers around Python CLIs.
# All business logic (validation, branching, verification) lives in Python.
# This keeps Make portable and consistent across dev/prod.



.PHONY: help dev-serve dev-smoke mcp-tools mcp-call docker-down-all test test-policy test-defaults test-groups \
		app-register token-import user-add auth-init auth-refresh auth-status \
		onboard-user prod-up prod-down

# .env 에서 PORT 파싱 (없으면 8081)
PORT := $(shell awk -F= '/^PORT=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(PORT)),)
	PORT := 8081
endif
# MCP_URL은 .env에서 읽지 않고 PORT만 사용
MCP_URL = http://localhost:$(PORT)

# Prefer uv (no venv activation needed); fallback to system python
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(strip $(UV)),)
	RUN := python
else
	RUN := uv run --
endif

# Compose 파일 경로(정리용)
COMPOSE_TOOL    = docker compose -f docker-compose-tool.yml --env-file .env
COMPOSE_ROOT    = docker compose -f docker-compose.yml   --env-file .env
COMPOSE_DIRECT  = docker compose -f docker-compose.yml -f docker-compose.direct.yml   --env-file .env
COMPOSE_TRAEFIK = docker compose -f docker-compose.yml -f docker-compose.traefik.yml  --env-file .env

help:
	@echo "Make targets (thin wrappers):"
	@echo "  dev-serve       : Start FastAPI locally (uv, foreground)"
	@echo "  dev-smoke       : Run local smoke tests"
	@echo "  mcp-tools       : Call tools/list against local server"
	@echo "  mcp-call        : Call arbitrary JSON-RPC method"
	@echo "  docker-down-all : Stop all compose stacks"
	@echo "  app-register    : Register/reuse app via helper (ADMIN_PROFILE, optional INTERACTIVE=1)"
	@echo "  group-list      : List policy groups"
	@echo "  group-put       : Upsert a policy group (GROUP, TOOLS, TAGS)"
	@echo "  group-del       : Delete a policy group (GROUP)"
	@echo "  policy-reload   : Reload Casbin enforcer (if configured)"
	@echo "  token-import    : Import a token JSON into DB profile (PROFILE, FROM_FILE or TOKEN)"
	@echo "  user-add        : Create API key for a user (USER, TOKEN_PROFILE or TOKEN_ID, optional APP_*)"
	@echo "  auth-init|refresh|status : Helper token ops"
	@echo "  onboard-user    : One-shot: token import + user add (USER, NAME, FROM_FILE)"
	@echo "  prod-up|prod-down : Start/stop production compose"
	@echo "Env: MCP_URL, ADMIN_API_KEY required for admin ops"

# ---------- Local development (uv) ----------


dev-serve:
	@echo "[dev] Loading .env and starting FastAPI (foreground) on port $(PORT)"
		bash -lc 'set -a; [ -f .env ] && . ./.env; set +a; \
		  TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
		  $(RUN) python -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload --reload-exclude "secrets/*"'


dev-smoke:
	@echo "[dev] Running smoke tests locally"
	ADMIN_API_KEY=$${ADMIN_API_KEY:-test-key} TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
		DB_URL=$${DB_URL:-sqlite:///./secrets/test.db} DB_AUTO_CREATE=true \
		$(RUN) python smoke_test.py

test:
	@echo "[test] curl smoke"
	bash tests/curl_smoke.sh

test-policy:
	@echo "[test] policy smoke"
	bash tests/policy_smoke.sh

test-defaults:
	@echo "[test] default policy smoke (role:all)"
	bash tests/default_policy_smoke.sh

test-groups:
	@echo "[test] groups smoke"
	bash tests/groups_smoke.sh

# ---------- JSON-RPC helpers ----------


# For MCP calls, use a per-user key (USER_API_KEY)
USER_API_KEY ?=
mcp-tools:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${USER_API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .

PARAMS ?= {}
mcp-call:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${USER_API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .

# ---------- Policy Groups (admin) ----------
GROUP ?=
TOOLS ?=
TAGS ?=

group-list:
	curl -sS $(MCP_URL)/admin/groups -H "x-api-key: ${ADMIN_API_KEY}" | jq .

group-put:
	@test -n "$(GROUP)" || (echo "Provide GROUP=name" && false)
			@tools_json=$$( $(RUN) python - <<-PY
			import os, json
			tools = [x for x in os.getenv('TOOLS','').split(',') if x.strip()]
			tags = [x for x in os.getenv('TAGS','').split(',') if x.strip()]
			print(json.dumps({"tools": tools, "tags": tags}))
		PY
		); \
	curl -sS -X PUT $(MCP_URL)/admin/groups/$(GROUP) -H 'content-type: application/json' -H "x-api-key: ${ADMIN_API_KEY}" -d "$$tools_json" | jq .

group-del:
	@test -n "$(GROUP)" || (echo "Provide GROUP=name" && false)
	curl -sS -X DELETE $(MCP_URL)/admin/groups/$(GROUP) -H "x-api-key: ${ADMIN_API_KEY}" | jq .

policy-reload:
	curl -sS -X POST $(MCP_URL)/admin/policy/reload -H "x-api-key: ${ADMIN_API_KEY}" | jq .

# ---------- Docker cleanup ----------

docker-down-all:
	-$(COMPOSE_DIRECT) down --remove-orphans
	-$(COMPOSE_TRAEFIK) down --remove-orphans
	-$(COMPOSE_ROOT) down --remove-orphans
	-$(COMPOSE_TOOL) down --remove-orphans

# ---------- DB & Auth Helper UX ----------

# DB 스키마는 서버 기동 시 자동 생성(ensure_schema). 별도 마이그레이션 도구 제거.
db-up:
	@echo "[db] no-op (schema auto-created on server start)"

# Usage: make app-register ADMIN_PROFILE=admin [INTERACTIVE=1]
#
# [권장] 먼저 'make app-register INTERACTIVE=1'로 대화형 로그인 시도하세요.
# 환경변수(ADMIN_TENANT_ID/ADMIN_CLIENT_ID/ADMIN_CLIENT_SECRET)로 자동화도 가능.
ADMIN_PROFILE ?= admin
INTERACTIVE ?=
app-register:
	@echo "[app-register] ADMIN_PROFILE=$(ADMIN_PROFILE)"
	@PORT=$(PORT) MCP_URL=$(MCP_URL) APP_PROFILE=$(ADMIN_PROFILE) $(RUN) python -m auth_helper.cli register-app $(if $(INTERACTIVE),--interactive,)

# Usage: make token-import PROFILE=alice FROM_FILE=./secrets/alice.json
#   or:  make token-import PROFILE=alice TOKEN='{"access_token":"..."}'
TOKEN ?=
FROM_FILE ?=
token-import:
	@test -n "$(PROFILE)" || (echo "PROFILE required (ex: PROFILE=alice)" && false)
	@if [ -n "$(FROM_FILE)" ]; then \
	  PORT=$(PORT) MCP_URL=$(MCP_URL) $(RUN) python -m app.cli profiles import --profile $(PROFILE) --from-file "$(FROM_FILE)"; \
	else \
	  test -n "$(TOKEN)" || (echo "Provide FROM_FILE=path or TOKEN='json'" && false); \
	  PORT=$(PORT) MCP_URL=$(MCP_URL) $(RUN) python -m app.cli profiles import --profile $(PROFILE) --token "$(TOKEN)"; \
	fi

# Usage: make user-add USER=alice NAME="Alice" [TEMPLATE=lite] [TOKEN_ID=1|TOKEN_PROFILE=alice] [APP_ID=1|APP_PROFILE=admin]
TOKEN_ID ?=
TOKEN_PROFILE ?=
APP_ID ?=
APP_PROFILE ?=
user-add:
	@test -n "$(USER)" || (echo "USER required (ex: USER=alice)" && false)
	@if [ -z "$(TOKEN_ID)" ] && [ -z "$(TOKEN_PROFILE)" ]; then \
	  echo "Provide TOKEN_ID or TOKEN_PROFILE" && false; \
	fi; \
	PORT=$(PORT) MCP_URL=$(MCP_URL) $(RUN) python -m app.cli users add \
	  --user-id "$(USER)" \
	  $(if $(NAME),--name "$(NAME)",) \
	  --template "$(if $(TEMPLATE),$(TEMPLATE),lite)" \
	  $(if $(TOKEN_ID),--token-id "$(TOKEN_ID)",) \
	  $(if $(TOKEN_PROFILE),--token-profile "$(TOKEN_PROFILE)",) \
	  $(if $(APP_ID),--app-id "$(APP_ID)",) \
	  $(if $(APP_PROFILE),--app-profile "$(APP_PROFILE)",)

auth-init:
	$(RUN) python -m auth_helper.cli init

auth-refresh:
	$(RUN) python -m auth_helper.cli refresh --slack-seconds 0

auth-status:
	$(RUN) python -m auth_helper.cli status

# ---------- One-shot onboarding ----------

# Usage: make onboard-user USER=alice NAME="Alice" FROM_FILE=./secrets/alice.json [TEMPLATE=lite] [APP_PROFILE=admin]
TEMPLATE ?=
FROM_FILE ?=
onboard-user:
	@test -n "$(USER)" || (echo "USER is required. ex) make onboard-user USER=alice NAME=Alice" && false)
	@test -n "$(FROM_FILE)$(TOKEN)" || (echo "Provide FROM_FILE=path or TOKEN='json'" && false)
	@if [ -n "$(FROM_FILE)" ]; then \
	  PORT=$(PORT) MCP_URL=$(MCP_URL) $(RUN) python -m app.cli users onboard --user-id "$(USER)" --name "$(NAME)" --template "$(if $(TEMPLATE),$(TEMPLATE),lite)" --token-profile "$(USER)" --from-file "$(FROM_FILE)" $(if $(APP_PROFILE),--app-profile "$(APP_PROFILE)",); \
	else \
	  PORT=$(PORT) MCP_URL=$(MCP_URL) $(RUN) python -m app.cli users onboard --user-id "$(USER)" --name "$(NAME)" --template "$(if $(TEMPLATE),$(TEMPLATE),lite)" --token-profile "$(USER)" --token "$(TOKEN)" $(if $(APP_PROFILE),--app-profile "$(APP_PROFILE)",); \
	fi

# ---------- Production (docker compose, direct) ----------

prod-up:
	$(COMPOSE_DIRECT) up -d

prod-down:
	$(COMPOSE_DIRECT) down --remove-orphans
