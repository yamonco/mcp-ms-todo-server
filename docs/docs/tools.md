---
sidebar_position: 4
---

# Tool Usage

## How to List Tools
Send a POST request to `/mcp` with:
```json
{
  "method": "tools/list",
  "params": {}
}
```

## How to Call a Tool
Send a POST request to `/mcp` with:
```json
{
  "method": "tools/call",
  "params": {
    "name": "<tool_name>",
    "arguments": { ... }
  }
}
```

## Example: Create a Task
```json
{
  "method": "tools/call",
  "params": {
    "name": "todo.create_task",
    "arguments": {
      "list_id": "<LIST_ID>",
      "title": "Prepare meeting"
    }
  }
}
```

## Tool Arguments
Refer to `tools/list` output for required arguments and schema for each tool.
