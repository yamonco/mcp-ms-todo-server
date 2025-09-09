# MCP-MS-Todo-Server 배포/운영 가이드

## 로컬 개발 실행
1. `.env` 파일 작성 (예시는 `.env.example` 참고)
2. `docker compose up -d` 실행
3. MCP 서버는 `http://localhost:8080/mcp`에서 동작
4. 테스트 후 `docker compose down`으로 종료

## 운영/클라우드 배포 (Traefik + HTTPS)
1. 도메인 준비 및 DNS 설정 (예: `mcp-todo.example.com`)
2. Traefik v2 역프록시가 서버 클러스터에 설정되어 있어야 함
3. `.env` 파일 작성 및 환경변수 채우기
4. `docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d` 실행
5. MCP 서버는 `https://mcp-todo.example.com/mcp`에서 동작

### Traefik 라벨 예시 (docker-compose.traefik.yml)
```
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.mcp.rule=Host(`mcp-todo.example.com`)"
  - "traefik.http.routers.mcp.entryPoints=websecure"
  - "traefik.http.routers.mcp.tls.certresolver=lets-encrypt"
  - "traefik.http.services.mcp.loadbalancer.server.port=8080"
  - "traefik.docker.network=traefik_public"
```

## 인증 모드
- 권장: authentik (OIDC)
  - `.env`에서 `AUTHENTIK_ENABLED=true`, `AUTHENTIK_ONLY=true`를 설정하고, 인트로스펙션 URL과 클라이언트 자격증명을 채웁니다.
  - 역할/그룹/권한은 스코프 및 클레임으로 전달됩니다(`mcp.admin`, `mcp.role:*`, `groups`).
  - 그래프 토큰은 커스텀 클레임(`graph_access_token`/`graph_refresh_token`)으로 전달하도록 매핑하세요.
- 호환: API Key
  - `.env`의 `ADMIN_API_KEY`를 강력한 값으로 설정하세요.
  - 사용자 API 키는 서버에서 발급되며, 호출 시 `X-API-Key`에 포함합니다.

## 개발 편의 (authentik)
- 로컬 통합 부팅: `make authentik-up` (Postgres/Redis 포함)
- 서버는 `.env`의 `AUTHENTIK_*` 값을 사용해 인트로스펙트합니다.

## 기타
- 운영 환경에서는 Traefik 네트워크와 certresolver 이름을 실제 환경에 맞게 수정하세요.
- MCP 서버는 기본적으로 모든 Origin을 차단(CORS 제한)하며, 필요시 특정 도메인만 허용하도록 변경 가능합니다.
