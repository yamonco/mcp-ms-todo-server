---
sidebar_position: 5
---

# 설정 (2025)

모든 설정은 환경 변수로 관리됩니다. JSON 토큰 파일은 사용하지 않습니다.

## 서버
- `PORT`, `LOG_LEVEL`, `API_KEY`, `ALLOW_ORIGINS`, `SSE_ENABLED`

## 데이터베이스
- `DB_URL`, `DB_ECHO`, `DB_AUTO_CREATE`

## Graph / Auth Helper
- `ADMIN_TENANT_ID`, `ADMIN_CLIENT_ID`, `ADMIN_CLIENT_SECRET`
- `APP_PREFIX` (기본: mcp-todo-server)
- `SCOPES` (기본: `Tasks.ReadWrite offline_access`)

## 툴 스키마
- `TOOL_SCHEMA_DIR` (기본: app/tools)

