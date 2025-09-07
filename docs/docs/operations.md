---
sidebar_position: 8
---

# Operations Guide

운영 단계에서 필요한 역할/권한 설계, API 키 회전, 토큰 로테이션 절차를 정리합니다.

## RBAC(역할/권한)
- 역할 저장소: DB 테이블 `roles`
- 역할 엔드포인트(관리자 키 필요):
  - `GET /admin/rbac/roles`
  - `PUT /admin/rbac/roles/{name}` — `{ "tools": ["todo.lists.get", ...] }`
  - `DELETE /admin/rbac/roles/{name}`
- API 키 메타의 `role`에 역할명을 지정하면, 서버는 역할의 툴 목록을 우선 적용합니다(키의 개별 allowed_tools보다 우선). 역할을 사용하면 대규모 사용자에 대한 권한 변경이 쉬워집니다.

## API 키 수명주기 & 회전
1) 신규 키 발급: `POST /admin/api-keys` (또는 `python -m app.cli users add`)
2) 점진적 전환: 클라이언트에게 새 키 배포 후, 일정 기간 구 키와 병행 운용
3) 구 키 폐기: `DELETE /admin/api-keys/{key}`
4) 권고사항:
   - 키에 메모/사용자 식별자를 남겨 추적성 확보(`note`, `user_id`, `name`)
   - 역할 기반 접근(RBAC) 사용으로 키 교체 시 권한 일관성 유지

## 토큰 로테이션(사용자 토큰)
시나리오 A — 동일 프로필 유지(무중단에 가까움):
1) 새 토큰 JSON 확보(오프라인 동의/보안 채널)
2) `POST /admin/tokens` with `{ profile: <same>, token: <json> }` 로 upsert
3) `GET /admin/tokens/by-profile/<profile>`로 확인
4) 사용자 API 키는 그대로(프로필 고정). 서비스는 새 토큰으로 자동 전환

시나리오 B — 새 프로필로 전환:
1) 새 프로필명으로 토큰 임포트
2) 해당 사용자 API 키를 `PATCH /admin/api-keys/{key}`로 `token_profile` 또는 `token_id` 갱신
3) 구 프로필은 일정 기간 후 삭제

주의사항:
- 헬퍼의 `refresh`는 refresh_token 존재가 전제입니다. 조직 정책상 주기적 재동의가 필요하면 새 토큰 JSON을 위 절차로 재반영하세요.

## 보안 권장사항
- `API_KEY`는 마스터 권한이므로 비밀로 보관, 회전 주기 운영
- DB 백업/암호화 적용, 접근 제어(네트워크/WAF)
- 관리자 앱(ADMIN_CLIENT_SECRET)도 주기적으로 갱신, 최소 권한 원칙 준수

## 가용성 & 모니터링
- `/health`: 상태 점검(헬스체크)
- `/metrics`: Prometheus 형식 지표 수집
- 에러 로깅/레벨은 `LOG_LEVEL`로 제어

