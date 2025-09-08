---
sidebar_position: 3
---

# API 레퍼런스 (DB‑first)

## JSON‑RPC 엔드포인트
- `POST /mcp`
  - `tools/list`: 사용 가능한 툴 목록(역할/허용툴에 따라 필터)
  - `tools/call`: 툴 실행(스키마 기반 검증)

### 예시 (tools/call)
```json
{ "method": "tools/call", "params": { "name": "todo.create_task", "arguments": { "list_id": "<LIST_ID>", "title": "Prepare" } } }
```

## 지원 툴(요약)
- `todo.lists.get`, `todo.lists.mutate`
- `todo.tasks.get`, `todo.tasks.create`, `todo.tasks.delete`, `todo.tasks.patch`
- `todo.tasks.lite_*`, `todo.sync.*` (활성화된 경우)

## 관리자 엔드포인트
- 키: `GET/POST/PATCH/DELETE /admin/api-keys`
- 토큰: `GET /admin/tokens`, `GET /admin/tokens/by-profile/{profile}`, `POST /admin/tokens`
  (역할/RBAC 제거: 사용자 키별 allowed_tools만 사용)
- 상태: `GET /admin/auth/status`
- 메트릭: `GET /metrics`

관리자 요청에는 `X-API-Key`가 필요합니다.

## 인증 모델 (DB 전용)
- 디바이스 코드 제거. 토큰은 DB `tokens` 테이블에 임포트/업서트됩니다.
- API 키는 `token_id` 또는 `token_profile`로 토큰을 참조합니다.
