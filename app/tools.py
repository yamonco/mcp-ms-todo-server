
 # tools.py (2025 MCP structure)
 # - MCP tool meta/executor definition
 # - ToolDef: name, description, inputSchema, exec
 # - validate_params_by_schema: tool parameter validation
 # - _list_tools: returns tool list
 # - _call_tool: executes tool and returns result


import os
import json
from typing import Dict, Any, Callable, Optional, List, Tuple
from app.container import get_todo_service
from app.config import cfg
import glob
from jsonschema import validate, ValidationError

todo_service = get_todo_service()

# 툴 실행 함수 매핑
TOOL_EXEC_MAP: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    # lists
    "todo.lists.get": lambda p: todo_service.list_lists(),
    "todo.lists.mutate": lambda p: todo_service.mutate_list(p),

    # tasks core
    "todo.tasks.get": lambda p: todo_service.list_tasks(p["list_id"], user=p.get("user")),
    "todo.tasks.create": lambda p: todo_service.create_task(
        p["list_id"], p["title"],
        body=p.get("body"), due=p.get("due"), time_zone=p.get("time_zone"),
        reminder=p.get("reminder"), importance=p.get("importance"), status=p.get("status"),
        recurrence=p.get("recurrence"),
    ),
    "todo.tasks.delete": lambda p: todo_service.delete_task(p["list_id"], p["task_id"]),
    "todo.tasks.patch": lambda p: (
        todo_service.update_task(p["list_id"], p["task_id"], p["patch"]) if p.get("mode", "generic") == "generic"
        else todo_service.complete_task(p["list_id"], p["task_id"]) if p.get("mode") == "complete"
        else todo_service.reopen_task(p["list_id"], p["task_id"]) if p.get("mode") == "reopen"
        else todo_service.snooze_task(p["list_id"], p["task_id"], p["remind_at_iso"], p.get("tz", "Asia/Seoul")) if p.get("mode") == "snooze"
        else {"error": f"unsupported patch mode: {p.get('mode')}"}
    ),

    # lite
    "todo.tasks.lite_list": lambda p: todo_service.list_tasks_lite(p["list_id"], top=p.get("top", 20)),
    "todo.tasks.lite_all": lambda p: todo_service.list_tasks_all_lite(p["list_id"], page_size=p.get("page_size", 100)),
    "todo.tasks.lite_complete": lambda p: todo_service.complete_task_lite(p["list_id"], p["task_id"]),
    "todo.tasks.lite_snooze": lambda p: todo_service.snooze_task_lite(p["list_id"], p["task_id"], p["remind_at_iso"], p.get("tz", "Asia/Seoul")),

    # delta/sync
    "todo.sync.delta_lists": lambda p: todo_service.delta_lists(delta_link=p.get("delta_link")),
    "todo.sync.delta_tasks": lambda p: todo_service.delta_tasks(p["list_id"], delta_link=p.get("delta_link")),
    "todo.sync.walk_delta_lists": lambda p: todo_service.walk_delta_lists(delta_link=p.get("delta_link")),
    "todo.sync.walk_delta_tasks": lambda p: todo_service.walk_delta_tasks(p["list_id"], delta_link=p.get("delta_link")),
}

# 외부 JSON 스키마 로딩
def load_tool_defs(schema_dir: str) -> List[Dict[str, Any]]:
    tool_defs = []
    for path in glob.glob(os.path.join(schema_dir, "*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            tool_defs.append(data)
    return tool_defs

TOOLS: List[Dict[str, Any]] = load_tool_defs(cfg.tool_schema_dir)
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
        if isinstance(raw, (dict, list)):
            return {"content": [{"type": "json", "json": raw}], "isError": False}
        if isinstance(raw, str):
            return {"content": [{"type": "text", "text": raw}], "isError": False}
        # fallback: stringify
        return {"content": [{"type": "text", "text": json.dumps(raw, ensure_ascii=False)}], "isError": False}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"tool failed: {str(e)}"}], "isError": True}
