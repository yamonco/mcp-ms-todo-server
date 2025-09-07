---
sidebar_position: 4
---

# Tool Usage (JSON‑RPC)

## List Tools
```json
{ "method": "tools/list", "params": {} }
```

## Call Tool
```json
{ "method": "tools/call", "params": { "name": "<tool_name>", "arguments": { /* per schema */ } } }
```

## Examples
Create Task:
```json
{ "method": "tools/call", "params": { "name": "todo.create_task", "arguments": { "list_id": "<LIST_ID>", "title": "Prepare" } } }
```

Note
- Actual schemas are returned by `tools/list` (name, description, inputSchema).
- Tool availability is filtered by your API key role/allowed_tools.
