# Minimal Makefile (authentik-first)

.PHONY: help guard run dev-serve dev-smoke mcp-tools mcp-call client-call \
        policy-reload docker-down-all prod-up prod-down authentik-up authentik-down

# Port and base URL
PORT := $(shell awk -F= '/^PORT=/{print $$2}' .env 2>/dev/null | tail -n1)
ifeq ($(strip $(PORT)),)
	PORT := 8081
endif
MCP_URL = http://localhost:$(PORT)

# Prefer uv
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(strip $(UV)),)
	RUN := python
else
	RUN := uv run --
endif

help:
	@echo "Targets: dev-serve, mcp-tools, mcp-call, policy-reload, authentik-up|down, prod-up|down"

guard:
	@test -f pyproject.toml -a -d app || (pwd; echo "[ERR] Run from repo root" >&2; exit 1)

run: guard dev-serve

dev-serve: guard
	@echo "[dev] start FastAPI on port $(PORT)"
	bash -lc 'set -a; [ -f .env ] && . ./.env; set +a; \
	  TOOL_SCHEMA_DIR=$${TOOL_SCHEMA_DIR:-./app/tools} \
	  $(RUN) python -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload --reload-exclude "secrets/*"'

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

client-call:
	@BEARER_TOKEN=$(BEARER_TOKEN) npx -y node client/mcp-client.mjs --url $(MCP_URL) --key $(BEARER_TOKEN) --method $(METHOD) --params '$(PARAMS)'

# Ops
policy-reload: guard
	$(RUN) python -m app.admin_cli policy-reload | jq .

# Docker
authentik-up: guard
	docker compose -f docker-compose.authentik.yml up -d

authentik-down: guard
	docker compose -f docker-compose.authentik.yml down --remove-orphans

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env up -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans

docker-down-all: guard
	-docker compose -f docker-compose.yml -f docker-compose.direct.yml --env-file .env down --remove-orphans
	-docker compose -f docker-compose-tool.yml --env-file .env down --remove-orphans
	-docker compose -f docker-compose.traefik.yml --env-file .env down --remove-orphans

