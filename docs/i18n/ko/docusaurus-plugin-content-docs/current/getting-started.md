---
sidebar_position: 2
---

# 시작하기 (Make + CLI)

## 사전 준비
- Docker 또는 로컬 Python(uvicorn)
- `DB_URL` 설정(기본 SQLite)

## 빠른 설정
```bash
cp .env.example .env
make db-up
make app-register PROFILE=admin

echo '{"access_token":"...","refresh_token":"...","expires_on":1736200000}' \
  | make token-import PROFILE=alice TOKEN='@-'

make user-add USER=alice NAME="Alice" TEMPLATE=lite TOKEN_PROFILE=alice
make dev-serve
```

## 원샷 온보딩
```bash
make onboard-user USER=alice NAME="Alice" FROM_FILE=./secrets/alice.json
```

## 툴 호출
- 목록: `make mcp-tools USER_API_KEY=<user_api_key>`
- 실행: `make mcp-call USER_API_KEY=<user_api_key> METHOD=tools/call PARAMS='{"name":"todo.lists.get","arguments":{}}'`
