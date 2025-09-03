
 # tools.py (2025 MCP structure)
 # - MCP tool meta/executor definition
 # - ToolDef: name, description, inputSchema, exec
 # - validate_params_by_schema: tool parameter validation
 # - _list_tools: returns tool list
 # - _call_tool: executes tool and returns result

from typing import Dict, Any, Callable, Optional, List, Tuple
from pydantic import BaseModel
from service_todo import TodoService

todo_service = TodoService()
ToolExec = Callable[[Dict[str, Any]], Any]

class ToolDef(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]
    exec: ToolExec

def validate_params_by_schema(params: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
    """Validate tool parameters according to JSON Schema (supports anyOf/oneOf)"""
    if not schema or schema.get("type") != "object":
        return None
    required = schema.get("required", [])
    props: Dict[str, Dict[str, Any]] = schema.get("properties", {})
    for r in required:
        if r not in params:
            return f"missing required field: {r}"
    type_map = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    for key, spec in props.items():
        if key in params and "type" in spec:
            py = type_map.get(spec["type"])
            if py and not isinstance(params[key], py):
                return f"invalid type for '{key}': expected {spec['type']}"
    # anyOf/oneOf (minimal required keys check)
    for alt in (schema.get("anyOf") or []) + (schema.get("oneOf") or []):
        req = alt.get("required", [])
        if not req or all(k in params for k in req):
            return None
    return None

from service_todo import TodoService
todo_service = TodoService()
TOOLS: List[ToolDef] = [
    ToolDef(
        name="todo.lists.get",
        description="Get todo list.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get"], "default": "get"}
            },
            "required": ["action"],
            "additionalProperties": False
        },
        exec=lambda p: todo_service.list_lists(),
    ),
    ToolDef(
        name="todo.lists.mutate",
        description="Create, delete, or rename list.",
        inputSchema={
            "type": "object",
            "oneOf": [
                {
                    "properties": {
                        "action": {"type": "string", "enum": ["create"]},
                        "display_name": {"type": "string"}
                    },
                    "required": ["action", "display_name"],
                    "additionalProperties": False
                },
                {
                    "properties": {
                        "action": {"type": "string", "enum": ["delete"]},
                        "list_id": {"type": "string"}
                    },
                    "required": ["action", "list_id"],
                    "additionalProperties": False
                },
                {
                    "properties": {
                        "action": {"type": "string", "enum": ["rename"]},
                        "list_id": {"type": "string"},
                        "display_name": {"type": "string"}
                    },
                    "required": ["action", "list_id", "display_name"],
                    "additionalProperties": False
                }
            ]
        },
        exec=lambda p: todo_service.mutate_list(p),
    ),
    ToolDef(
        name="todo.tasks.get",
        description="Get tasks in list.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get"], "default": "get"},
                "list_id": {"type": "string"},
                "lite": {"type": "boolean"},
                "top": {"type": "integer"},
                "user": {"type": "string"}
            },
            "required": ["action", "list_id"],
            "additionalProperties": False
        },
        exec=lambda p: todo_service.list_tasks(p["list_id"], user=p.get("user")),
    ),
    ToolDef(
        name="todo.tasks.delete",
        description="Delete task permanently.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["delete"], "default": "delete"},
                "list_id": {"type": "string"},
                "task_id": {"type": "string"}
            },
            "required": ["action", "list_id", "task_id"],
            "additionalProperties": False
        },
        exec=lambda p: todo_service.delete_task(p["list_id"], p["task_id"]),
    ),
    ToolDef(
        name="todo.tasks.create",
        description="Create new task.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create"], "default": "create"},
                "list_id": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "due": {"type": "string", "description": "ISO8601"},
                "time_zone": {"type": "string"},
                "reminder": {"type": "string", "description": "ISO8601"},
            },
            "required": ["action", "list_id", "title"],
            "additionalProperties": False
        },
        exec=lambda p: todo_service.create_task(p["list_id"], p["title"], body=p.get("body"), due=p.get("due"), time_zone=p.get("time_zone"), reminder=p.get("reminder")),
    ),
]

TOOLS_BY_NAME: Dict[str, ToolDef] = {t.name: t for t in TOOLS}

def _list_tools(cursor: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return tool list (tools/list)"""
    tool_defs = []
    for t in TOOLS:
        tool_defs.append({
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema
        })
    return tool_defs, None

def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool and return result (tools/call)"""
    if name not in TOOLS_BY_NAME:
        raise ValueError("Unknown tool")
    tool = TOOLS_BY_NAME[name]
    err = validate_params_by_schema(arguments or {}, tool.inputSchema)
    if err:
        raise TypeError(err)
    try:
        raw = tool.exec(arguments or {})
        if isinstance(raw, dict) and "content" in raw and "isError" in raw:
            return raw
        if isinstance(raw, str):
            text = raw
        else:
            text = json.dumps(raw, ensure_ascii=False)
        return {
            "content": [
                {"type": "text", "text": text}
            ],
            "isError": False
        }
    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"tool failed: {str(e)}"}
            ],
            "isError": True
        }
