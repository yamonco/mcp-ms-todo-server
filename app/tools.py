
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
    """Validate tool parameters according to JSON Schema"""
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
    return None

TOOLS: List[ToolDef] = [
    # Actual ToolDef definitions are managed in main.py
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
