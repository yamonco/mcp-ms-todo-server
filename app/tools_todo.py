import os, json
from typing import Dict, Any, Optional

from .auth_msal import get_access_token, start_device_code_flow, poll_device_code_flow, logout
from . import adapter_graph_rest as rest

def tool_auth_start_device_code(_: Dict[str, Any]) -> Dict[str, Any]:
    flow = start_device_code_flow()
    return {"type":"device_code", **flow}

def tool_auth_status(_: Dict[str, Any]) -> Dict[str, Any]:
    res = poll_device_code_flow()
    return res

def tool_auth_logout(_: Dict[str, Any]) -> Dict[str, Any]:
    logout()
    return {"status":"ok"}

def _token() -> str:
    tokens = get_access_token()
    return tokens["access_token"]

# ---- Lists ----
def tool_list_lists(_: Dict[str, Any]) -> Dict[str, Any]:
    return rest.list_lists(_token())

def tool_create_list(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.create_list(_token(), p["display_name"])

def tool_update_list(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.update_list(_token(), p["list_id"], p.get("display_name"))

# ---- Tasks ----
def tool_list_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.list_tasks(_token(), p["list_id"], p.get("filter"), p.get("top"))

def tool_get_task(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.get_task(_token(), p["list_id"], p["task_id"])

def tool_create_task(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.create_task(
        _token(),
        list_id=p["list_id"],
        title=p["title"],
        body=p.get("body"),
        due=p.get("due"),
        time_zone=p.get("time_zone", "Asia/Seoul"),
        reminder=p.get("reminder"),
        importance=p.get("importance"),
        status=p.get("status"),
        recurrence=p.get("recurrence"),
    )

def tool_update_task(p: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if "title" in p: patch["title"] = p["title"]
    if "status" in p: patch["status"] = p["status"]
    if "due" in p: patch["dueDateTime"] = {"dateTime": p["due"], "timeZone": p.get("time_zone","Asia/Seoul")}
    if "reminder" in p: patch["reminderDateTime"] = {"dateTime": p["reminder"], "timeZone": p.get("time_zone","Asia/Seoul")}
    if "importance" in p: patch["importance"] = p["importance"]
    if "body" in p: patch["body"] = {"content": p["body"], "contentType": "text"}
    return rest.update_task(_token(), p["list_id"], p["task_id"], patch)

def tool_delete_task(p: Dict[str, Any]) -> Dict[str, Any]:
    rest.delete_task(_token(), p["list_id"], p["task_id"])
    return {"status":"deleted"}

# ---- Delta ----
def tool_delta_lists(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.delta_lists(_token(), p.get("delta_link"))

def tool_delta_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.delta_tasks(_token(), p["list_id"], p.get("delta_link"))

TOOLS = {
    "auth.start_device_code": tool_auth_start_device_code,
    "auth.status": tool_auth_status,
    "auth.logout": tool_auth_logout,
    "todo.list_lists": tool_list_lists,
    "todo.create_list": tool_create_list,
    "todo.update_list": tool_update_list,
    "todo.list_tasks": tool_list_tasks,
    "todo.get_task": tool_get_task,
    "todo.create_task": tool_create_task,
    "todo.update_task": tool_update_task,
    "todo.delete_task": tool_delete_task,
    "todo.delta_lists": tool_delta_lists,
    "todo.delta_tasks": tool_delta_tasks,
}
