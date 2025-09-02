---
sidebar_position: 3
---

# API Reference

## Endpoints
- `/mcp` (POST): Main JSON-RPC endpoint

## Tool Methods
- `tools/list`: Returns available tools
- `tools/call`: Executes a tool with arguments

## Example Request
```json
{
  "method": "tools/call",
  "params": {
    "name": "todo.create_task",
    "arguments": {
      "list_id": "<LIST_ID>",
      "title": "Prepare meeting",
      "body": "Agenda summary",
      "due": "2025-09-05T09:00:00",
      "time_zone": "Asia/Seoul"
    }
  }
}
```

## Supported Tools
- `todo.lists.get`: Get list of lists
- `todo.lists.mutate`: Create/Delete/Rename list
- `todo.tasks.get`: Get list of tasks
- `todo.tasks.create`: Create task
- `todo.tasks.delete`: Delete task
- `todo.tasks.patch`: Update/complete/reopen/snooze task
- `todo.sync.delta`: Sync/change detection

---

# Authentication Tools
- `auth.start_device_code`: Start device code flow
- `auth.status`: Check device code flow status
- `auth.logout`: Logout
