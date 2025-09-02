import os, json
from typing import Dict, Any, Optional
import httpx

GRAPH = "https://graph.microsoft.com/v1.0"

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# ---- Lists ----
def list_lists(token: str) -> Dict[str, Any]:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{GRAPH}/me/todo/lists", headers=_headers(token))
        r.raise_for_status()
        return r.json()

def create_list(token: str, display_name: str) -> Dict[str, Any]:
    body = {"displayName": display_name}
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{GRAPH}/me/todo/lists", headers=_headers(token), json=body)
        r.raise_for_status()
        return r.json()

def update_list(token: str, list_id: str, display_name: Optional[str]=None) -> Dict[str, Any]:
    patch = {}
    if display_name is not None:
        patch["displayName"] = display_name
    with httpx.Client(timeout=30) as c:
        r = c.patch(f"{GRAPH}/me/todo/lists/{list_id}", headers=_headers(token), json=patch)
        r.raise_for_status()
        return r.json()

# ---- Tasks ----
def list_tasks(token: str, list_id: str, filter_expr: Optional[str]=None, top: Optional[int]=None) -> Dict[str, Any]:
    params = {}
    if filter_expr: params["$filter"] = filter_expr
    if top: params["$top"] = str(top)
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{GRAPH}/me/todo/lists/{list_id}/tasks", headers=_headers(token), params=params)
        r.raise_for_status()
        return r.json()

def get_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", headers=_headers(token))
        r.raise_for_status()
        return r.json()

def create_task(token: str, list_id: str, title: str, body: Optional[str]=None,
                due: Optional[str]=None, time_zone: Optional[str]="Asia/Seoul",
                reminder: Optional[str]=None, importance: Optional[str]=None,
                status: Optional[str]=None, recurrence: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"title": title}
    if body: payload["body"] = {"content": body, "contentType": "text"}
    if due: payload["dueDateTime"] = {"dateTime": due, "timeZone": time_zone or "UTC"}
    if reminder: payload["reminderDateTime"] = {"dateTime": reminder, "timeZone": time_zone or "UTC"}
    if importance: payload["importance"] = importance
    if status: payload["status"] = status
    if recurrence: payload["recurrence"] = recurrence

    with httpx.Client(timeout=30) as c:
        r = c.post(f"{GRAPH}/me/todo/lists/{list_id}/tasks", headers=_headers(token), json=payload)
        r.raise_for_status()
        return r.json()

def update_task(token: str, list_id: str, task_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=30) as c:
        r = c.patch(f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", headers=_headers(token), json=patch)
        r.raise_for_status()
        return r.json()

def delete_task(token: str, list_id: str, task_id: str) -> None:
    with httpx.Client(timeout=30) as c:
        r = c.delete(f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", headers=_headers(token))
        r.raise_for_status()

# ---- Delta ----
def delta_lists(token: str, delta_link: Optional[str]=None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/delta"
    with httpx.Client(timeout=30) as c:
        r = c.get(url, headers=_headers(token))
        r.raise_for_status()
        return r.json()

def delta_tasks(token: str, list_id: str, delta_link: Optional[str]=None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/{list_id}/tasks/delta"
    with httpx.Client(timeout=30) as c:
        r = c.get(url, headers=_headers(token))
        r.raise_for_status()
        return r.json()
