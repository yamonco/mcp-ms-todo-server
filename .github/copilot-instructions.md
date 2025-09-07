# Copilot Instructions for MCP-MS-TODO-SERVER

## Overview
This project is a FastAPI-based MCP server integrating Microsoft To Do (Graph API) with MCP (Microsoft Cloud Platform). All features are exposed via a single JSON-RPC endpoint (`/mcp`) using a tool system. The architecture is designed for Docker-based deployment and supports REST, SSE (streaming), and optional PowerShell execution.

## Architecture & Key Components
- **app/**: Main server code. Entry point is `main.py`. Core logic is split into:
  - `tools.py`: Tool definitions and dispatch
  - `domain/`, `usecases/`, `infrastructure/`: Clean architecture layers
  - `container.py`, `config.py`: Dependency injection and configuration
- **secrets/**: Stores authentication tokens and sensitive data. Never commit contents.
- **tools/**: JSON schemas for tool definitions (used for validation and documentation)
- **auth-helper/**: Standalone helper for authentication flows
- **Dockerfile & docker-compose.yml**: Containerization and orchestration

## Developer Workflows
- **Build & Run**:
  ```bash
  cp .env.example .env
  docker compose build
  docker compose up -d
  ```
- **Authentication**:
  1. Call `auth.start_device_code` via tools/call
  2. Complete device code flow in browser
  3. Confirm with `auth.status`
- **Tool Invocation**:
  - List tools: `POST /mcp` `{ "method": "tools/list", "params": {} }`
  - Call tool: `POST /mcp` `{ "method": "tools/call", "params": { "name": "<tool_name>", "arguments": { ... } } }`
- **Testing**:
  - Manual/curl: See `tests/README.md` and `curl_smoke.sh`
  - Python: `smoke_test.py` in root and `app/`

## Project-Specific Patterns
- All business logic is accessed via the tools/call system. Avoid direct REST endpoint additions.
- Service layer (e.g., `TodoService`) separates Graph API calls from business logic.
- Comments should reflect MCP protocol, JSON-RPC 2.0, and tools/call usage. Remove legacy REST comments.
- Environment variables are critical for security and configuration. Never commit `.env` or `secrets/`.
- Only delegated permissions are supported for Microsoft To Do integration.

## Integration Points
- **Microsoft Graph API**: Used for all To Do operations. See `infrastructure/msgraph_repository.py`.
- **PowerShell (optional)**: For advanced scenarios, see `pwsh/` scripts.
- **Token management**: Handled via device code flow and stored in `secrets/`.

## Examples
- Get tasks:
  ```json
  {
    "method": "tools/call",
    "params": {
      "name": "todo.tasks.get",
      "arguments": { "action": "get", "list_id": "<LIST_ID>" }
    }
  }
  ```
- Create task:
  ```json
  {
    "tool": "todo.create_task",
    "params": { "list_id": "<LIST_ID>", "title": "Prepare meeting" }
  }
  ```

## References
- See `README.md` for full API and workflow documentation
- See `app/` for main server logic and tool definitions
- See `tests/README.md` for test setup and usage

---
For unclear or missing sections, please provide feedback to improve these instructions.
