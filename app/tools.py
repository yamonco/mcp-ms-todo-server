
 # tools.py (2025 MCP structure)
 # - MCP tool meta/executor definition
 # - ToolDef: name, description, inputSchema, exec
 # - validate_params_by_schema: tool parameter validation
 # - _list_tools: returns tool list
 # - _call_tool: executes tool and returns result


import os
import json
from typing import Dict, Any, Callable, Optional, List, Tuple
from app.container import get_todo_service_for
from app.config import cfg
from app.context import get_current_user_meta
from app import rbac
import glob
from jsonschema import validate, ValidationError

def _service():
    meta = get_current_user_meta() or {}
    # DB 기반: token_id 또는 token_profile (프로필명)만 지원
    token_id = meta.get("token_id") if isinstance(meta.get("token_id"), int) else None
    token_profile = meta.get("token_profile") or None
    return get_todo_service_for(token_profile, token_id=token_id)

# 툴 실행 함수 매핑
TOOL_EXEC_MAP: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    # lists
    "todo.lists.get": lambda p: _service().list_lists(),
    "todo.lists.mutate": lambda p: _service().mutate_list(p),

    # tasks core
    "todo.tasks.get": lambda p: _service().list_tasks(p["list_id"], user=p.get("user"), top=p.get("top")),
    "todo.tasks.create": lambda p: _service().create_task(
        p["list_id"], p["title"],
        body=p.get("body"), due=p.get("due"), time_zone=p.get("time_zone"),
        reminder=p.get("reminder"), importance=p.get("importance"), status=p.get("status"),
        recurrence=p.get("recurrence"),
    ),
    "todo.tasks.delete": lambda p: _service().delete_task(p["list_id"], p["task_id"]),
    "todo.tasks.patch": lambda p: (
        _service().update_task(p["list_id"], p["task_id"], p["patch"]) if p.get("mode", "generic") == "generic"
        else _service().complete_task(p["list_id"], p["task_id"]) if p.get("mode") == "complete"
        else _service().reopen_task(p["list_id"], p["task_id"]) if p.get("mode") == "reopen"
        else _service().snooze_task(p["list_id"], p["task_id"], p["remind_at_iso"], p.get("tz", "Asia/Seoul")) if p.get("mode") == "snooze"
        else {"error": f"unsupported patch mode: {p.get('mode')}"}
    ),

    # lite
    "todo.tasks.lite_list": lambda p: _service().list_tasks_lite(p["list_id"], top=p.get("top", 20)),
    "todo.tasks.lite_all": lambda p: _service().list_tasks_all_lite(p["list_id"], page_size=p.get("page_size", 100)),
    "todo.tasks.lite_complete": lambda p: _service().complete_task_lite(p["list_id"], p["task_id"]),
    "todo.tasks.lite_snooze": lambda p: _service().snooze_task_lite(p["list_id"], p["task_id"], p["remind_at_iso"], p.get("tz", "Asia/Seoul")),

    # delta/sync
    "todo.sync.delta_lists": lambda p: _service().delta_lists(delta_link=p.get("delta_link")),
    "todo.sync.delta_tasks": lambda p: _service().delta_tasks(p["list_id"], delta_link=p.get("delta_link")),
    "todo.sync.walk_delta_lists": lambda p: _service().walk_delta_lists(delta_link=p.get("delta_link")),
    "todo.sync.walk_delta_tasks": lambda p: _service().walk_delta_tasks(p["list_id"], delta_link=p.get("delta_link")),
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
    tool_defs: List[Dict[str, Any]] = []
    for t in TOOLS:
        tool_defs.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "inputSchema": t.get("inputSchema", {})
        })
    # Centralized filtering by current user's allowed_tools (if any)
    meta = get_current_user_meta() or {}
    # RBAC role 우선 적용(default는 전체 허용)
    role = (meta.get("role") or "").strip()
    allowed = None
    if role:
        allowed = rbac.resolve_allowed_tools_for_role(role)
    # 키에 개별 allowed_tools가 있으면 교차/대체
    if isinstance(allowed, list) and allowed:
        names = set(allowed)
        tool_defs = [td for td in tool_defs if td.get("name") in names]
    else:
        key_tools = meta.get("allowed_tools")
        if isinstance(key_tools, list) and key_tools:
            names = set(key_tools)
            tool_defs = [td for td in tool_defs if td.get("name") in names]
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
