# MCP 서버 클라이언트 등록 안내 (Cursor/Claude Code)

## VSCode Cursor에서 MCP 서버 등록
1. `.mcp.json` 파일을 프로젝트 루트에 복사/생성 (예시는 `.mcp.json.example` 참고)
2. MCP 호출에는 사용자 키(`USER_API_KEY`)를 사용합니다. 관리용 마스터 키는 `ADMIN_API_KEY`로 분리되어 `.env`에만 보관하세요.
3. Cursor에서 프로젝트 열면 MCP 서버 등록 안내가 자동으로 뜨며, 승인 후 사용 가능

### .mcp.json 예시 (X-API-Key 헤더)
```
{
  "mcpServers": {
    "todo-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "X-API-Key": "${USER_API_KEY}"
      },
      "env": {
        "USER_API_KEY": "your-user-api-key-here"
      }
    }
  }
}
```

### 대안: Authorization 헤더 사용 (Bearer)
```
{
  "mcpServers": {
    "todo-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer ${USER_API_KEY}"
      },
      "env": {
        "USER_API_KEY": "your-user-api-key-here"
      }
    }
  }
}
```

둘 중 어느 방식이든 동작합니다. 일부 클라이언트는 `Authorization`만 지원하므로 상황에 맞게 선택하세요. 쿼리 파라미터(`?x-api-key=...`)도 지원하지만 헤더 사용을 권장합니다.

## 환경변수 치환
- `${USER_API_KEY}` 등 변수는 사용자의 환경에서 자동 치환됨
- 민감 정보는 절대 .mcp.json에 직접 입력하지 말고, 환경변수로 관리

## Claude Desktop/다른 클라이언트
- Desktop 앱은 설정 파일에 MCP 서버 정보를 직접 입력하거나, Cursor에서 내보내기(import) 기능을 활용
- 동일한 .mcp.json 구조를 사용하므로, 복사/이관이 용이

## 보안 주의사항
- 사용자 키는 각 사용자별로 발급받아 사용하고, 관리자 키(`ADMIN_API_KEY`)는 관리자 엔드포인트에서만 사용하세요.
- .mcp.json, .env 파일은 .gitignore에 포함하여 커밋 금지

## 참고
- 자세한 배포/운영 방법은 `README_DEPLOY.md` 참고
