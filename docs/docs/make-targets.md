---
sidebar_position: 7
---

# Make Targets Guide

이 문서는 제공되는 Make 타겟을 한 곳에 정리합니다. 빠르게 서버를 세팅/운영하고, 앱 등록/토큰 임포트/유저 생성/테스트를 CLI 중심으로 수행할 수 있습니다.

## 공통 전제
- `.env`에 최소 다음 값을 설정합니다
  - `API_KEY`: 서버 관리자 키(강력한 랜덤)
  - `DB_URL`: 예) `sqlite:///./secrets/app.db`
  - `PORT`: 개발 포트(기본 8081)
  - 앱 등록 시: `ADMIN_TENANT_ID`, `ADMIN_CLIENT_ID`, `ADMIN_CLIENT_SECRET`

## DB & 서버
- `make db-up`
  - Alembic 마이그레이션을 최신으로 적용합니다.

- `make dev-serve`
  - 로컬 개발 서버를 uvicorn으로 기동합니다(`--reload`).

- `make prod-up` / `make prod-down`
  - docker compose 기반 프로덕션 모드 기동/종료(구성 파일 참조).

- `make docker-down-all`
  - repo 내 compose 스택을 모두 정리합니다.

## 앱 등록(App Registration)
- `make app-register PROFILE=admin`
  - Microsoft Graph API로 앱을 등록/재사용하고, 결과 메타(CLIENT_ID/TENANT_ID/SCOPES)를 DB의 토큰 프로필에 저장합니다.
  - 비인터랙티브(권장): `.env`에 `ADMIN_TENANT_ID`, `ADMIN_CLIENT_ID`, `ADMIN_CLIENT_SECRET`가 있어야 합니다.
  - 인터랙티브(대화형): 자격이 없거나 테스트용으로 `make app-register PROFILE=admin INTERACTIVE=1`

Behavior
- If `CLIENT_ID` and `TENANT_ID` are set in environment, the helper simply copies them into DB (no Graph call).
- Otherwise it reuses by `APP_PREFIX` (latest) or creates a new app via Graph, then saves meta to DB.

비고(한국어)
- 환경변수에 앱 정보가 지정되어 있으면 그대로 DB에 복사하고, 없으면 Graph API로 재사용/생성을 수행합니다.

예시(비인터랙티브):
```bash
make app-register PROFILE=admin
```

예시(인터랙티브):
```bash
make app-register PROFILE=admin INTERACTIVE=1
```

## 토큰 임포트(Token Import)
- `make token-import PROFILE=<name> FROM_FILE=./secrets/alice.json`
- 또는 `make token-import PROFILE=<name> TOKEN='{"access_token":"...","refresh_token":"..."}'`
  - 원시 토큰 JSON을 DB 프로필로 저장합니다(파일/문자열 둘 다 지원).

## 사용자 추가(User Add)
- `make user-add USER=alice NAME="Alice" TEMPLATE=lite TOKEN_PROFILE=alice`
- 또는 `make user-add USER=alice TEMPLATE=lite TOKEN_ID=1`
  - API 키를 생성하고 DB 토큰과 연결합니다.
  - `TEMPLATE`는 툴 권한 세트를 지정(lite/default/custom). RBAC 역할이 있다면 서버에서 역할 우선 적용.

## 원샷 온보딩(One-shot)
- `make onboard-user USER=alice NAME="Alice" FROM_FILE=./secrets/alice.json`
  - 토큰 임포트 + 유저 생성까지 한 번에 수행합니다.

## 인증 헬퍼(보조)
- `make auth-init`
  - refresh_token 기반으로 토큰 유효성/갱신을 수행(디바이스 코드 없음).

- `make auth-refresh`
  - 만료까지 여유가 없어도 즉시 갱신 시도(slack 0초).

- `make auth-status`
  - 헬퍼가 조회 가능한 토큰 상태를 출력.

## MCP 호출 도우미
- `make mcp-tools API_KEY=<user_api_key>`
  - 현재 키로 호출 가능한 툴 목록을 확인합니다.

- `make mcp-call API_KEY=<user_api_key> METHOD=tools/call PARAMS='{"name":"todo.lists.get","arguments":{}}'`
  - 임의의 JSON-RPC 호출을 수행합니다.
