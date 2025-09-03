
.PHONY: help \
	tool-build tool-up tool-down tool-exec az-cli-login az-login app-register set-tenant tool-account tool-token \
	server-build server-up server-down server-logs server-restart \
	mcp-init mcp-tools mcp-raw mcp-call mcp-manifest \
	docs-install docs-build docs-start docs-serve
## MCP manifest 자동 생성
mcp-manifest:
	python3 tools_manifest.py

COMPOSE_TOOL = docker compose -f docker-compose-tool.yml --env-file .env
COMPOSE_ROOT    = docker compose -f docker-compose.yml   --env-file .env
COMPOSE_DIRECT  = docker compose -f docker-compose.yml -f docker-compose.direct.yml   --env-file .env
COMPOSE_TRAEFIK = docker compose -f docker-compose.yml -f docker-compose.traefik.yml  --env-file .env

TOOL_SERVICE   = auth-tool
SERVER_SERVICE = mcp

# .env 에서 PORT 파싱
PORT := $(shell awk -F= '/^PORT=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(PORT)),)
  PORT := 8081
endif
MCP_URL = http://localhost:$(PORT)

help:
	@echo "Targets:"
	@echo "  tool-build       : Build auth-helper image"
	@echo "  tool-up          : Start auth-helper container"
	@echo "  tool-down        : Stop auth-helper container"
	@echo "  az-cli-login     : Azure CLI login (auto tenant/subscription switch)"
	@echo "  app-register     : Register Azure AD app (Tasks.ReadWrite) + save metadata"
	@echo "  az-login         : Issue/refresh MSAL device code token (token.json)"
	@echo "  tool-exec        : Run auth-helper.py with custom command (ex: make tool-exec CMD=\"status\")"
	@echo "  set-tenant       : Save TENANT_ID to token.json (ex: make set-tenant TENANT=...)"
	@echo "  tool-account     : Show current Azure CLI context"
	@echo "  tool-token       : Check token.json metadata/expiration"
	@echo "  server-build     : Build MCP server image"
	@echo "  server-up        : Start MCP server"
	@echo "  server-down      : Stop MCP server"
	@echo "  server-logs      : Follow MCP server logs"
	@echo "  server-restart   : Restart MCP server"
	@echo "  server-up-direct : Start MCP server (direct port mapping)"
	@echo "  server-down-direct: Stop MCP server (direct stack)"
	@echo "  server-up-traefik: Start MCP server (Traefik labels)"
	@echo "  server-down-traefik: Stop MCP server (Traefik stack)"
	@echo "  mcp-init         : Call MCP initialize"
	@echo "  mcp-tools        : Call MCP tools/list"
	@echo "  mcp-raw          : Raw MCP tools/list response"
	@echo "  mcp-call         : Call arbitrary method (ex: make mcp-call METHOD=tools/list PARAMS='{}')"
	@echo "  docs-install     : Install Docusaurus deps (in ./docs)"
	@echo "  docs-build       : Build Docusaurus site (./docs/build)"
	@echo "  docs-start       : Start Docusaurus dev server"
	@echo "  docs-serve       : Serve built site locally"

# ---------- Tool (auth-helper) ----------

tool-build:
	$(COMPOSE_TOOL) build --no-cache

tool-up:
	$(COMPOSE_TOOL) up -d

tool-down:
	$(COMPOSE_TOOL) down

# Azure CLI 로그인
az-cli-login:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc '\
		if [ -n "$$TENANT_ID" ]; then \
			echo "[az login] tenant=$$TENANT_ID"; \
			az login --tenant "$$TENANT_ID"; \
		else \
			echo "[az login] tenant not set → interactive device login"; \
			az login; \
			TID=$$(az account show --query tenantId -o tsv 2>/dev/null || true); \
			if [ -n "$$TID" ]; then \
				echo "[sync] detected TENANT_ID=$$TID → token.json 반영"; \
				python3 -u /opt/auth-helper/auth-helper.py set-tenant --tenant "$$TID"; \
			else \
				echo "[sync] tenantId 감지 실패(수동 지정 필요)"; \
			fi; \
		fi; \
		if [ -n "$$AZ_SUBSCRIPTION_ID" ]; then \
			echo "[az account set] subscription=$$AZ_SUBSCRIPTION_ID"; \
			az account set --subscription "$$AZ_SUBSCRIPTION_ID"; \
		fi'

# 앱 등록
app-register:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc '\
		if ! az account show >/dev/null 2>&1; then \
			echo "[precheck] az not logged in → running az login"; \
			if [ -n "$$TENANT_ID" ]; then az login --tenant "$$TENANT_ID"; else az login; fi; \
		fi; \
		python3 -u /opt/auth-helper/auth-helper.py register-app'

# 디바이스 코드 토큰 발급/갱신
az-login:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc 'python3 -u /opt/auth-helper/auth-helper.py init'

# helper 임의 실행: make tool-exec CMD="status"
tool-exec:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc 'python3 -u /opt/auth-helper/auth-helper.py $(CMD)'

# Run one-shot refresh (uses refresh_token if needed)
tool-refresh:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc 'REFRESH_SLACK=$${REFRESH_SLACK:-600} python3 -u /opt/auth-helper/auth-helper.py refresh --slack-seconds $$REFRESH_SLACK'

# Start auto refresh loop inside helper container
tool-auto-refresh:
	$(COMPOSE_TOOL) exec -d $(TOOL_SERVICE) sh -lc 'REFRESH_INTERVAL=$${REFRESH_INTERVAL:-60}; REFRESH_SLACK=$${REFRESH_SLACK:-600}; python3 -u /opt/auth-helper/auth-helper.py auto-refresh --interval-seconds $$REFRESH_INTERVAL --slack-seconds $$REFRESH_SLACK'

# token.json 에 TENANT_ID 저장: make set-tenant TENANT=<uuid>
set-tenant:
	@test -n "$(TENANT)" || (echo "TENANT 가 필요합니다. 예: make set-tenant TENANT=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" && false)
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) sh -lc 'python3 -u /opt/auth-helper/auth-helper.py set-tenant --tenant "$(TENANT)"'

tool-account:
	$(COMPOSE_TOOL) exec $(TOOL_SERVICE) az account show -o table || true

tool-token:
	@echo "[host] ./secrets/token.json preview:"
	@sh -lc 'if command -v jq >/dev/null 2>&1; then jq "{CLIENT_ID,TENANT_ID,SCOPES,expires_on}" ./secrets/token.json; else head -c 400 ./secrets/token.json; fi || true'

# ---------- MCP server ----------

server-build:
	$(COMPOSE_ROOT) build --no-cache

server-up:
	$(COMPOSE_ROOT) up -d

server-down:
	$(COMPOSE_ROOT) down

# Prefer explicit mode commands
server-up-direct:
	# Ensure Traefik stack is not running to avoid label/network conflicts
	-$(COMPOSE_TRAEFIK) down --remove-orphans
	$(COMPOSE_DIRECT) up -d

server-down-direct:
	$(COMPOSE_DIRECT) down --remove-orphans

server-up-traefik:
	# Ensure direct stack is not running to avoid port conflicts
	-$(COMPOSE_DIRECT) down --remove-orphans
	$(COMPOSE_TRAEFIK) up -d

server-down-traefik:
	$(COMPOSE_TRAEFIK) down --remove-orphans

server-logs:
	$(COMPOSE_ROOT) logs -f

server-restart:
	$(COMPOSE_ROOT) down
	$(COMPOSE_ROOT) up -d

# Run in-container smoke test (requires server container running)
server-smoke:
	$(COMPOSE_ROOT) exec $(SERVER_SERVICE) sh -lc 'API_KEY=$${API_KEY:-test-key} TOOL_SCHEMA_DIR=/app/app/tools python -m app.smoke_test'

# ---------- MCP JSON-RPC convenience ----------

mcp-init:
		curl -sS $(MCP_URL)/mcp \
		  -H 'Content-Type: application/json' \
		  -H "x-api-key: ${API_KEY}" \
		  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}' | jq '.result.tools'

mcp-tools:
		curl -sS $(MCP_URL)/mcp \
		  -H 'Content-Type: application/json' \
		  -H "x-api-key: ${API_KEY}" \
		  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .
mcp-raw:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .
PARAMS ?= {}
mcp-call:
	curl -sS $(MCP_URL)/mcp \
	  -H 'Content-Type: application/json' \
	  -H "x-api-key: ${API_KEY}" \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .

# ---------- Docs (Docusaurus) ----------

DOCS_DIR=./docs

docs-install:
	cd $(DOCS_DIR) && npm ci

docs-build:
	cd $(DOCS_DIR) && npm run build

docs-start:
	cd $(DOCS_DIR) && npm start

docs-serve:
	cd $(DOCS_DIR) && npm run serve
