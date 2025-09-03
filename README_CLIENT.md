# MCP 서버 클라이언트 등록 안내 (Cursor/Claude Code)

## VSCode Cursor에서 MCP 서버 등록
1. `.mcp.json` 파일을 프로젝트 루트에 복사/생성 (예시는 `.mcp.json.example` 참고)
2. `API_KEY` 환경변수는 반드시 `.env`에 설정하고, 노출되지 않게 관리
3. Cursor에서 프로젝트 열면 MCP 서버 등록 안내가 자동으로 뜨며, 승인 후 사용 가능

### .mcp.json 예시
```
{
  "mcpServers": {
    "todo-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "X-API-Key": "${API_KEY}"
      },
      "env": {
        "API_KEY": "your-secure-api-key-here"
      }
    }
  }
}
```

## 환경변수 치환
- `${API_KEY}` 등 변수는 사용자의 환경에서 자동 치환됨
- 민감 정보는 절대 .mcp.json에 직접 입력하지 말고, 환경변수로 관리

## Claude Desktop/다른 클라이언트
- Desktop 앱은 설정 파일에 MCP 서버 정보를 직접 입력하거나, Cursor에서 내보내기(import) 기능을 활용
- 동일한 .mcp.json 구조를 사용하므로, 복사/이관이 용이

## 보안 주의사항
- API Key는 반드시 복잡하게 생성하고, 외부에 노출되지 않게 관리
- .mcp.json, .env 파일은 .gitignore에 포함하여 커밋 금지

## 참고
- 자세한 배포/운영 방법은 `README_DEPLOY.md` 참고
