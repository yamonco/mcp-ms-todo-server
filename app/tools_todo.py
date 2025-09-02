def tool_auth_start_device_code(_: Dict[str, Any]) -> Dict[str, Any]:
def tool_auth_status(_: Dict[str, Any]) -> Dict[str, Any]:
def tool_auth_logout(_: Dict[str, Any]) -> Dict[str, Any]:
def _token() -> str:
def tool_list_lists(_: Dict[str, Any]) -> Dict[str, Any]:
def tool_create_list(p: Dict[str, Any]) -> Dict[str, Any]:
def tool_list_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
def _token() -> str:

# tools_todo.py (2025 MCP 구조)
# - 인증/리스트/태스크 관련 툴 함수 정의
# - 각 함수는 MCP 툴 실행기에서 호출됨

import os
import json
from typing import Dict, Any, Optional, List

from auth_msal import (
    get_access_token,
    start_device_code_flow,
    poll_device_code_flow,
    logout,
)
import adapter_graph_rest as rest

# 인증 관련 툴
def tool_auth_start_device_code(_: Dict[str, Any]) -> Dict[str, Any]:
    """Device code flow 시작"""
    flow = start_device_code_flow()
    return {"type": "device_code", **flow}

def tool_auth_status(_: Dict[str, Any]) -> Dict[str, Any]:
    """Device code flow 상태 확인"""
    return poll_device_code_flow()

def tool_auth_logout(_: Dict[str, Any]) -> Dict[str, Any]:
    """로그아웃"""
    logout()
    return {"status": "ok"}

def _token() -> str:
    """현재 인증 토큰 반환"""
    tokens = get_access_token()
    return tokens["access_token"]

# 리스트 관련 툴
def tool_list_lists(_: Dict[str, Any]) -> Dict[str, Any]:
    """리스트 목록 조회"""
    return rest.list_lists(_token())

def tool_create_list(p: Dict[str, Any]) -> Dict[str, Any]:
    """리스트 생성"""
    return rest.create_list(_token(), p["display_name"])

def tool_update_list(p: Dict[str, Any]) -> Dict[str, Any]:
    """리스트 이름 변경"""
    return rest.update_list(_token(), p["list_id"], p.get("display_name"))

# 태스크 관련 툴
def tool_list_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
    """태스크 목록 조회"""
    config_path = Path('/app/secrets/token.json')
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config.get("access_token", "")
    return ""
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
    if "title" in p:
        patch["title"] = p["title"]
    if "status" in p:
        patch["status"] = p["status"]
    if "due" in p:
        patch["dueDateTime"] = {
            "dateTime": p["due"],
            "timeZone": p.get("time_zone", "Asia/Seoul"),
        }
    if "reminder" in p:
        patch["reminderDateTime"] = {
            "dateTime": p["reminder"],
            "timeZone": p.get("time_zone", "Asia/Seoul"),
        }
    if "importance" in p:
        patch["importance"] = p["importance"]
    if "body" in p:
        patch["body"] = {"content": p["body"], "contentType": "text"}
    return rest.update_task(_token(), p["list_id"], p["task_id"], patch)


def tool_delete_task(p: Dict[str, Any]) -> Dict[str, Any]:
    rest.delete_task(_token(), p["list_id"], p["task_id"])
    return {"status": "deleted"}


 # ---------------------------
 # Delta
 # ---------------------------
def tool_delta_lists(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.delta_lists(_token(), p.get("delta_link"))


def tool_delta_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
    return rest.delta_tasks(_token(), p["list_id"], p.get("delta_link"))


# ---------------------------
# (Optional but recommended) Convenience tools
# ---------------------------
def tool_create_task_by_list_name(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Support for cases where only list_name is provided.
    """
    li = rest.find_or_create_list(_token(), p["list_name"])
    return rest.create_task(
        _token(),
        list_id=li["id"],
        title=p["title"],
        body=p.get("body"),
        due=p.get("due"),
        time_zone=p.get("time_zone", "Asia/Seoul"),
        reminder=p.get("reminder"),
        importance=p.get("importance"),
        status=p.get("status"),
        recurrence=p.get("recurrence"),
    )


def tool_get_task_select(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query only specific fields ($select, $expand)
    """
    return rest.get_task_select(
        _token(),
        p["list_id"],
        p["task_id"],
        select=p.get("select"),
        expand=p.get("expand"),
    )


def tool_batch_get_tasks(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Batch query multiple tasks using $batch
    """
    return rest.batch_get_tasks(_token(), p["list_id"], p["task_ids"])


 # ---------------------------
 # Tool registry
 # ---------------------------
TOOLS: Dict[str, Any] = {
    # Auth
    "auth.start_device_code": tool_auth_start_device_code,
    "auth.status": tool_auth_status,
    "auth.logout": tool_auth_logout,

    # Lists
    "todo.list_lists": tool_list_lists,
    "todo.create_list": tool_create_list,
    "todo.update_list": tool_update_list,
    "todo.delete_list": tool_delete_list,

    # Tasks
    "todo.list_tasks": tool_list_tasks,
    "todo.get_task": tool_get_task,
    "todo.create_task": tool_create_task,
    "todo.update_task": tool_update_task,
    "todo.delete_task": tool_delete_task,

    # Delta
    "todo.delta_lists": tool_delta_lists,
    "todo.delta_tasks": tool_delta_tasks,

    # Convenience (optional)
    "todo.create_task_by_list_name": tool_create_task_by_list_name,
    "todo.get_task_select": tool_get_task_select,
    # Auth
    # "auth.start_device_code": tool_auth_start_device_code,
    # "auth.status": tool_auth_status,
    # "auth.logout": tool_auth_logout,
    "todo.delete_task": tool_delete_task,
