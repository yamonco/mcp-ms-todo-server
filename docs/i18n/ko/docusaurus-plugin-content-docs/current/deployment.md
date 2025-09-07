---
sidebar_position: 6
---

# 배포

## Docker Compose (권장)
```bash
cp .env.example .env
make db-up
make app-register PROFILE=admin
make dev-serve  # 또는 make prod-up
```

환경 변수에 `API_KEY`, `DB_URL`, `ADMIN_*`를 설정하세요. 운영 환경에서는 리버스 프록시 및 DB 영속 볼륨 구성을 권장합니다.

## 상태/지표
- 헬스체크: `GET /health`
- 메트릭: `GET /metrics` (Prometheus)

## 문제 해결
- 서버 로그/`LOG_LEVEL` 확인
- DB 연결(`DB_URL`) 확인
- 앱 메타(`/admin/tokens/by-profile/<profile>`)와 사용자 API 키 생성 여부 확인

