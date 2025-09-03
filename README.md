
# License & Open Source Notice

This project is released under the MIT License by our organization. You are free to use, modify, distribute, and use it commercially. See the LICENSE file for details.


# MCP-MS-TODO-SERVER (2025 Latest MCP Structure)

This is an API server that integrates Microsoft To Do (Graph API) with MCP (Microsoft Cloud Platform). It is a FastAPI-based MCP server, and all features are provided via a single JSON-RPC endpoint (`/mcp`) using the tool system. You can quickly deploy and operate in a Docker environment, supporting Streamable HTTP (SSE), REST, and PowerShell (Microsoft.Graph) execution.

---


## Project Structure

```
mcp-ms-todo-server/
├── .env.example         # Example environment variable file
├── Dockerfile           # Docker image build settings
├── README.md            # Project description and usage
├── app/                 # Server application code (main.py, service_todo.py, tools.py, etc.)
├── docker-compose.yml   # Docker Compose settings
├── secrets/             # Private data such as authentication tokens
```

---


## Main Features

- **MCP JSON-RPC 2.0 Tool Server**: All features are called via `tools/list`, `tools/call`
- **Microsoft To Do (Graph API) Integration**: Supports authentication and CRUD operations
- **Streamable HTTP (SSE)**: Real-time progress log streaming
- **REST/PowerShell Execution**: REST by default, optional PowerShell (Microsoft.Graph)
- **Docker-based Deployment**: .env configuration, persistent token/log volumes

---


## Quick Start

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

---


## MCP Tool Invocation (2025 Standard)

- All features are provided via a single JSON-RPC endpoint (`/mcp`) using `tools/list`, `tools/call`
- List tools: `POST /mcp` with `{ "method": "tools/list", "params": {} }`
- Call tool: `POST /mcp` with `{ "method": "tools/call", "params": { "name": "<tool_name>", "arguments": { ... } } }`

### Example: Get Task List
```json
{
  "method": "tools/call",
  "params": {
    "name": "todo.tasks.get",
    "arguments": {
      "action": "get",
      "list_id": "<LIST_ID>"
    }
  }
}
```

Tool list/parameters can be checked from the `tools/list` result.

### Authentication Flow (Device Code)
1. Client calls MCP tool `auth.start_device_code`
2. Server returns `user_code`, `verification_uri` via SSE
3. Enter code in browser and approve
4. Confirm authentication completion with `auth.status`

---

## Main API Usage Examples

### Create Task
`POST /mcp/tools/call` (SSE or regular JSON)

```json
{
  "tool": "todo.create_task",
  "params": {
    "list_id": "<LIST_ID>",
    "title": "Prepare meeting",
    "body": "Agenda summary",
    "due": "2025-09-05T09:00:00",
    "time_zone": "Asia/Seoul"
  }
}
```



### Supported Tools (tools/list result)
- todo.lists.get: Get list of lists
- todo.lists.mutate: Create/Delete/Rename list
- todo.tasks.get: Get list of tasks
- todo.tasks.create: Create task
- todo.tasks.delete: Delete task

※ 현재 MCP 서버는 위 툴만 지원하며, tools.patch, sync.delta 등은 향후 확장 예정입니다. 실제 tools/list 결과와 코드/스키마 명칭이 일치하도록 관리합니다.

---



## Environment Variables (.env)

- `API_KEY`: MCP 서버 인증용 키 (반드시 복잡하게 설정, 외부 노출 금지)
- `TENANT_ID`: organizations|consumers|common or actual tenant ID
- `CLIENT_ID`: Set when registering app, leave blank for personal/public client
- `SCOPES`: Recommended value `Tasks.ReadWrite offline_access`
- `EXECUTOR_MODE`: `rest` (recommended) or `pwsh`
## MCP 서버 인증/보안

- 모든 /mcp 요청은 `X-API-Key` 헤더에 환경변수 `API_KEY` 값을 포함해야 인증됩니다.
- CORS 정책은 기본적으로 모든 Origin을 차단하며, 필요시 특정 도메인만 허용 가능합니다.
- API_KEY는 .env에만 저장하고, .gitignore에 반드시 포함시켜 커밋 금지.

---


## How to Run & Troubleshooting

1. Copy `.env.example` to `.env` and set environment variables
2. Build and run Docker image
3. After authentication, call API to integrate with Microsoft To Do (tools/call)
4. For PowerShell mode, refer to scripts and modules in pwsh/

### FAQ

- Authentication fails: Check `TENANT_ID`, `CLIENT_ID`, `SCOPES` values
- SSE logs not received: Check client SSE support
- PowerShell mode error: Check modules and dependencies in pwsh/

---


## Extensions & References

- Graph API Official Docs: https://docs.microsoft.com/en-us/graph/api/overview
- MCP server structure & extension: See code in app/ folder (main.py, service_todo.py, tools.py, etc.)

---

For questions and feedback, please leave an issue.
- PORT: Container internal 8080 fixed — expose external port as this value
- TZ, LOG_LEVEL


## Notes
- To Do works on **Delegated permissions** only. Application permissions are not officially supported.
- Periodic re-login may be required depending on organization MFA/security policy.
- `.env` and `secrets/` directories must be kept private.

## Latest Comment Writing Guide (without code changes)

- At the top of each file, specify "2025 MCP latest structure, JSON-RPC 2.0, tools/call system"
- For function/class comments, update to reflect actual MCP protocol flow, parameter structure, exception handling, etc.
- Remove outdated REST/direct call comments, unify with tools/call-based explanations
- Service layer (e.g., TodoService) should emphasize separation of Graph API/business logic
