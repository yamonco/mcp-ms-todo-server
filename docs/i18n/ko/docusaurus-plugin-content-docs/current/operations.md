---
sidebar_position: 8
---

# 운영 가이드

## RBAC
- 역할 관리: `GET/PUT/DELETE /admin/rbac/roles`
- API 키의 `role`로 역할을 지정하면 역할의 툴 목록이 우선 적용됩니다.

## API 키 회전
1) 새 키 발급 → 2) 병행 운용 → 3) 구 키 폐기
권고: `note`, `user_id`, `name` 메타로 추적성 확보

## 토큰 로테이션
- 동일 프로필 갱신: `POST /admin/tokens`로 같은 `profile`에 업서트 → 서비스 무중단 전환
- 새 프로필 전환: 새 프로필 생성 → API 키의 `token_profile`/`token_id` 갱신 → 구 프로필 정리

## 보안/가용성
- `API_KEY`/ADMIN 비밀은 주기적으로 교체하고 최소권한으로 유지
- `/health`, `/metrics` 제공. 로그는 `LOG_LEVEL`로 제어

