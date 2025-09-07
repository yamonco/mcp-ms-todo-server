---
sidebar_position: 7
---

# Make 타겟 가이드

## DB & 서버
- `make db-up`: 마이그레이션 적용
- `make dev-serve`: 개발 서버 기동
- `make prod-up` / `make prod-down`: 운영 모드 기동/종료

## 앱 등록
- `make app-register PROFILE=admin`
  - env에 `CLIENT_ID`/`TENANT_ID`가 있으면 DB에 복사
  - 없으면 Graph로 재사용/생성 후 메타 저장
- `INTERACTIVE=1`로 대화형 로그인 지원

## 토큰 임포트
- `make token-import PROFILE=alice FROM_FILE=./secrets/alice.json`
- 또는 `make token-import PROFILE=alice TOKEN='{"access_token":"..."}'`

## 사용자 생성
- `make user-add USER=alice NAME="Alice" TEMPLATE=lite TOKEN_PROFILE=alice`
- 또는 `make user-add USER=alice TEMPLATE=lite TOKEN_ID=1`

## 원샷
- `make onboard-user USER=alice NAME="Alice" FROM_FILE=./secrets/alice.json`

## 헬퍼
- `make auth-init` / `make auth-refresh` / `make auth-status`

