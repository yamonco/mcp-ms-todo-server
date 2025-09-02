.PHONY: help \
        tool-build tool-up tool-down tool-exec az-cli-login az-login app-register set-tenant tool-account tool-token \
        server-build server-up server-down server-logs server-restart \
        mcp-init mcp-tools mcp-raw mcp-call

COMPOSE_TOOL = docker compose -f docker-compose-tool.yml --env-file .env
COMPOSE_ROOT = docker compose -f docker-compose.yml   --env-file .env

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
	@echo "  tool-build       : auth-helper 이미지 빌드"
	@echo "  tool-up          : auth-helper 컨테이너 up"
	@echo "  tool-down        : auth-helper 컨테이너 down"
	@echo "  az-cli-login     : Azure CLI 로그인(tenant/subscription 자동 분기)"
	@echo "  app-register     : Azure AD 앱 등록(Tasks.ReadWrite) + 메타 저장"
	@echo "  az-login         : MSAL 디바이스 코드 토큰 발급/갱신(token.json)"
	@echo "  tool-exec        : auth-helper.py 임의 실행 (예: make tool-exec CMD=\"status\")"
	@echo "  set-tenant       : token.json 에 TENANT_ID 저장 (예: make set-tenant TENANT=...)"
	@echo "  tool-account     : 현재 Azure CLI 컨텍스트 표시"
	@echo "  tool-token       : token.json 메타/만료 필드 확인"
	@echo "  server-build     : MCP 서버 이미지 빌드"
	@echo "  server-up        : MCP 서버 up"
	@echo "  server-down      : MCP 서버 down"
	@echo "  server-logs      : MCP 서버 로그 팔로우"
	@echo "  server-restart   : MCP 서버 재시작"
	@echo "  mcp-init         : MCP initialize 호출"
	@echo "  mcp-tools        : MCP tools/list 호출"
	@echo "  mcp-raw          : MCP tools/list 원응답"
	@echo "  mcp-call         : 임의 메서드 호출 (예: make mcp-call METHOD=tools/list PARAMS='{}')"

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

server-logs:
	$(COMPOSE_ROOT) logs -f

server-restart:
	$(COMPOSE_ROOT) restart

# ---------- MCP JSON-RPC convenience ----------

mcp-init:
	curl -sS $(MCP_URL) \
	  -H 'Content-Type: application/json' \
	  -H 'Accept: application/json, text/event-stream' \
	  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-05-01","clientInfo":{"name":"make-cli","version":"0.1.0"},"capabilities":{}}}' | jq .

mcp-tools:
	curl -sS $(MCP_URL) \
	  -H 'Content-Type: application/json' \
	  -H 'Accept: application/json, text/event-stream' \
	  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}' | jq '.result.tools'

mcp-raw:
	curl -sS $(MCP_URL) \
	  -H 'Content-Type: application/json' \
	  -H 'Accept: application/json, text/event-stream' \
	  -d '{"jsonrpc":"2.0","id":"tools-raw","method":"tools/list","params":{}}' | jq .

METHOD ?= tools/list
PARAMS ?= {}
mcp-call:
	curl -sS $(MCP_URL) \
	  -H 'Content-Type: application/json' \
	  -H 'Accept: application/json, text/event-stream' \
	  -d '{"jsonrpc":"2.0","id":"call-1","method":"$(METHOD)","params":$(PARAMS)}' | jq .
