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

## 환경변수 및 인증
- 반드시 `.env`의 `API_KEY` 값을 복잡하게 설정하고, 외부에 노출하지 마세요.
- Cursor/Claude Code에서 MCP 서버 등록 시 `.mcp.json`에 아래와 같이 헤더를 추가:
```
"headers": { "X-API-Key": "${API_KEY}" }
```

## 기타
- 운영 환경에서는 Traefik 네트워크와 certresolver 이름을 실제 환경에 맞게 수정하세요.
- MCP 서버는 기본적으로 모든 Origin을 차단(CORS 제한)하며, 필요시 특정 도메인만 허용하도록 변경 가능합니다.
