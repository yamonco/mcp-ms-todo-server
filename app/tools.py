
 # tools.py (2025 MCP structure)
 # - MCP tool meta/executor definition
 # - ToolDef: name, description, inputSchema, exec
 # - validate_params_by_schema: tool parameter validation
 # - _list_tools: returns tool list
 # - _call_tool: executes tool and returns result


import os
import json
import logging
from typing import Dict, Any, Callable, Optional, List, Tuple
from app.container import get_todo_service_for
from app.config import cfg
from app.context import get_current_user_meta
from app import policy
import glob
from jsonschema import validate, ValidationError

logger = logging.getLogger("tools")


def _service():
    meta = get_current_user_meta() or {}
    # authentik-only: rely on bearer-derived token; DB profile not required
    if cfg.authentik_only or (cfg.authentik_enabled and meta.get("authentik_access_token")):
        return get_todo_service_for(None, token_id=None)
    # DB 기반: token_id 또는 token_profile (프로필명) 필요
    token_id = meta.get("token_id") if isinstance(meta.get("token_id"), int) else None
    token_profile = meta.get("token_profile") or None
    if not token_id and not token_profile:
        raise RuntimeError("User API key required: provide a key bound to token_profile/token_id (authentik bearer also allowed if AUTHENTIK_ENABLED)")
    return get_todo_service_for(token_profile, token_id=token_id)

def _explicit_exec(name: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
    """특수 케이스 전용 매핑(일반 규칙으로 매핑 불가한 것들)"""
    if name == "todo.lists.mutate":
        return lambda p: _service().mutate_list(p)
    if name == "todo.tasks.patch":
        return lambda p: (
            _service().update_task(p["list_id"], p["task_id"], p["patch"]) if p.get("mode", "generic") == "generic"
            else _service().complete_task(p["list_id"], p["task_id"]) if p.get("mode") == "complete"
            else _service().reopen_task(p["list_id"], p["task_id"]) if p.get("mode") == "reopen"
            else _service().snooze_task(p["list_id"], p["task_id"], p["remind_at_iso"], p.get("tz", "Asia/Seoul")) if p.get("mode") == "snooze"
            else {"error": f"unsupported patch mode: {p.get('mode')}"}
        )
    return None


def _auto_exec(name: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
    """컨벤션 기반 자동 매핑.
    - todo.lists.get        -> list_lists()
    - todo.tasks.get        -> list_tasks(**args)
    - todo.tasks.create     -> create_task(**args)
    - todo.tasks.delete     -> delete_task(**args)
    - todo.tasks.lite_list  -> list_tasks_lite(**args)
    - todo.tasks.lite_all   -> list_tasks_all_lite(**args)
    - todo.tasks.lite_*     -> *_lite(**args)
    - todo.sync.*           -> same name methods
    """
    parts = name.split(".")
    if len(parts) < 3 or parts[0] != "todo":
        return None
    domain, action = parts[1], ".".join(parts[2:])
    svc = _service

    # lists
    if domain == "lists":
        if action == "get":
            return lambda p: svc().list_lists()
        return None

    # tasks
    if domain == "tasks":
        if action in {"get", "create", "delete"}:
            method = {
                "get": "list_tasks",
                "create": "create_task",
                "delete": "delete_task",
            }[action]
            return lambda p, m=method: getattr(svc(), m)(**p)
        if action.startswith("lite_"):
            lite_map = {
                "lite_list": "list_tasks_lite",
                "lite_all": "list_tasks_all_lite",
                "lite_complete": "complete_task_lite",
                "lite_snooze": "snooze_task_lite",
            }
            method = lite_map.get(action)
            if method:
                return lambda p, m=method: getattr(svc(), m)(**p)
        return None

    # sync
    if domain == "sync":
        sync_methods = {"delta_lists", "delta_tasks", "walk_delta_lists", "walk_delta_tasks"}
        if action in sync_methods:
            return lambda p, m=action: getattr(svc(), m)(**p)
        return None

    return None

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
# tag index for quick lookup
_TAG_INDEX: Dict[str, set[str]] = {}
for t in TOOLS:
    for tag in set(t.get("tags", []) or []):
        _TAG_INDEX.setdefault(tag, set()).add(t.get("name"))

# 툴 실행 함수 매핑(동적 생성 + 특수 케이스 병합)
TOOL_EXEC_MAP: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
for tname in TOOLS_BY_NAME.keys():
    fn = _explicit_exec(tname) or _auto_exec(tname)
    if fn:
        TOOL_EXEC_MAP[tname] = fn
# 안전장치: 누락된 필수 툴 최소 바인딩(과거 매핑 유지)
TOOL_EXEC_MAP.setdefault("todo.lists.get", lambda p: _service().list_lists())

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
    # Policy engine filter (Casbin): single source of truth
    meta = get_current_user_meta() or {}
    tool_defs = policy.filter_tools_for(meta, tool_defs)
    return tool_defs, None

# helper for other modules
def tools_by_tags(tags: list[str]) -> list[str]:
    out: set[str] = set()
    for tg in tags or []:
        out |= _TAG_INDEX.get(tg, set())
    return sorted(out)


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool and return result (tools/call)"""
    if name not in TOOLS_BY_NAME:
        raise ValueError("Unknown tool")
    tool = TOOLS_BY_NAME[name]
    err = validate_params_by_schema(arguments or {}, tool.get("inputSchema", {}))
    if err:
        raise TypeError(err)
    try:
        # Casbin-only enforcement for simplicity
        meta = get_current_user_meta() or {}
        if not policy.enforce_tool(meta, name):
            raise PermissionError("Access denied by policy")
        exec_fn = TOOL_EXEC_MAP.get(name) or _explicit_exec(name) or _auto_exec(name)
        if not exec_fn:
            raise ValueError("No exec function mapped for tool")
        logger.debug(f"tool.call name={name} args_keys={list((arguments or {}).keys())}")
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
