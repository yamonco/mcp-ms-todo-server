---
sidebar_position: 3
---

# Automate To Do Tasks with MCP

Learn how to automate Microsoft To Do tasks using MCP-MS-TODO-SERVER.

## Example: List Tasks

Send a POST request to `/mcp`:

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