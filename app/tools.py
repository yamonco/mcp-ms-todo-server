
 # tools.py (2025 MCP structure)
 # - MCP tool meta/executor definition
 # - ToolDef: name, description, inputSchema, exec
 # - validate_params_by_schema: tool parameter validation
 # - _list_tools: returns tool list
 # - _call_tool: executes tool and returns result


import os
import json
from typing import Dict, Any, Callable, Optional, List, Tuple
from service_todo import TodoService
import glob
from jsonschema import validate, ValidationError

todo_service = TodoService()

# 툴 실행 함수 매핑
TOOL_EXEC_MAP: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "todo.lists.get": lambda p: todo_service.list_lists(),
    "todo.lists.mutate": lambda p: todo_service.mutate_list(p),
    "todo.tasks.get": lambda p: todo_service.list_tasks(p["list_id"], user=p.get("user")),
    "todo.tasks.delete": lambda p: todo_service.delete_task(p["list_id"], p["task_id"]),
    "todo.tasks.create": lambda p: todo_service.create_task(p["list_id"], p["title"], body=p.get("body"), due=p.get("due"), time_zone=p.get("time_zone"), reminder=p.get("reminder")),
}

# 외부 JSON 스키마 로딩
def load_tool_defs(schema_dir: str) -> List[Dict[str, Any]]:
    tool_defs = []
    for path in glob.glob(os.path.join(schema_dir, "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            tool_defs.append(data)
    return tool_defs

TOOLS: List[Dict[str, Any]] = load_tool_defs(os.path.join(os.path.dirname(__file__), "tools"))
TOOLS_BY_NAME: Dict[str, Dict[str, Any]] = {t["name"]: t for t in TOOLS}

def validate_params_by_schema(params: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
    try:
        validate(instance=params, schema=schema)
        return None
    except ValidationError as e:
        return str(e)


def _list_tools(cursor: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return tool list (tools/list)"""
    tool_defs = []
    for t in TOOLS:
        tool_defs.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "inputSchema": t.get("inputSchema", {})
        })
    return tool_defs, None


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool and return result (tools/call)"""
    if name not in TOOLS_BY_NAME:
        raise ValueError("Unknown tool")
    tool = TOOLS_BY_NAME[name]
    err = validate_params_by_schema(arguments or {}, tool.get("inputSchema", {}))
    if err:
        raise TypeError(err)
    try:
        exec_fn = TOOL_EXEC_MAP.get(name)
        if not exec_fn:
            raise ValueError("No exec function mapped for tool")
        raw = exec_fn(arguments or {})
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
