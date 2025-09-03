# MCP-MS-Todo-Server 운영/테스트 품질 가이드

## Health Check 및 모니터링
- `/health` 엔드포인트는 서버 상태, 버전, 인증 필요 여부 등 반환
- Traefik/모니터링 시스템에서 주기적으로 `/health`를 체크하여 서비스 가용성 확인

## Dockerfile 보안/최적화 권장
- `USER` 지시어로 루트가 아닌 사용자로 앱 실행
- 불필요한 패키지/캐시 제거, 이미지 경량화
- 필요한 포트만 expose, secrets/환경변수는 외부에서 주입

## .gitignore 관리
- `.env`, `.mcp.json`, secrets 등 민감 파일은 반드시 `.gitignore`에 포함
- 예시:
```
.env
.mcp.json
secrets/
```

## 통합 테스트/CI 권장
- MCP 서버 주요 엔드포인트(`/mcp`, `/health`)에 대한 통합 테스트 스크립트 작성
- CI에서 스키마-코드 동기화, Docker 이미지 취약점 검사 등 자동화
- 예시: pytest, curl, GitHub Actions 등 활용

## 참고
- 배포/클라이언트/환경변수 설정은 `README_DEPLOY.md`, `README_CLIENT.md` 참고
