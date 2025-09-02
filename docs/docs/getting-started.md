---
sidebar_position: 2
---

# Getting Started

## Prerequisites
- Node.js 18+
- Docker (recommended for deployment)

## Installation

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

## Authentication
- Device Code flow is used for Microsoft To Do API access.
- See the API Reference for tool usage (`auth.start_device_code`, `auth.status`).

## API Usage
- All features are exposed via a single JSON-RPC endpoint `/mcp`.
- Use `tools/list` to discover available tools.
- Use `tools/call` to execute tools.

---

# Example: Get Task List

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
