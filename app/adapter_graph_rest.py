# ./app/adapter_graph_rest.py
    return {

 # adapter_graph_rest.py (2025 MCP structure)
 # - Microsoft Graph API integration adapter
 # - REST calls based on access token, includes error/rate limiter/circuit breaker utilities

import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Callable, Iterator, Literal, List

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"

def _headers(token: str) -> Dict[str, str]:
    """Return headers for Graph API call"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

class GraphAPIError(Exception):
    """Graph API error wrapper"""
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status}:{code}:{message}")
        self.status = status
        self.code = code
        self.message = message

class _RateLimiter:
    """Simple token bucket rate limiter"""
    def __init__(self, rate_per_sec: float, burst: int):
        self.capacity = burst
        self.tokens = burst
        self.rate = rate_per_sec
        self.last = time.time()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = time.time()
            delta = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + delta * self.rate)
            if self.tokens < 1:
                sleep_for = (1 - self.tokens) / self.rate
                time.sleep(sleep_for)
                self.tokens = 0
            else:
                self.tokens -= 1

class _CircuitBreaker:
    """Simple circuit breaker"""
    def __init__(self, fail_threshold: int = 3, cooldown_sec: int = 5):
        self.fail = 0
        self.open_until = 0.0
        self.fail_threshold = fail_threshold
        self.cooldown_sec = cooldown_sec
        self.lock = threading.Lock()

    def before(self):
        with self.lock:
            if ok:
                self.fail = 0
            else:
                self.fail += 1
                if self.fail >= self.fail_threshold:
                    self.open_until = time.time() + self.cooldown_sec

_rate_limiter = _RateLimiter(rate_per_sec=5, burst=5)   # 5 per second, burst 5 (can be tuned for production)
_circuit = _CircuitBreaker(fail_threshold=3, cooldown_sec=5)  # block for 5 seconds after 3 failures

 # -----------------------------
 # MCP API facade function sample
 # -----------------------------
def todo_delta_lists(token: str, delta_link: str = None) -> Dict[str, Any]:
    """
    Get delta of lists
    """
    return delta_lists(token, delta_link)

def todo_delta_tasks(token: str, list_id: str, delta_link: str = None) -> Dict[str, Any]:
    """태스크 델타 조회"""
    return delta_tasks(token, list_id, delta_link)

def todo_walk_delta_lists(token: str, delta_link: str = None) -> Dict[str, Any]:
    """리스트 델타 전체 순회"""
    return walk_delta_lists(token, delta_link)

def todo_walk_delta_tasks(token: str, list_id: str, delta_link: str = None) -> Dict[str, Any]:
    """태스크 델타 전체 순회"""
    return walk_delta_tasks(token, list_id, delta_link)

def todo_find_or_create_list(token: str, display_name: str) -> Dict[str, Any]:
    """리스트가 없으면 생성"""
    return find_or_create_list(token, display_name)

def todo_quick_task(token: str, list_name: str, title: str, **kwargs) -> Dict[str, Any]:
    """빠른 태스크 생성(list_name 기반)"""
    return quick_task(token, list_name, title, **kwargs)

def todo_complete_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    """태스크 완료 처리"""
    return complete_task(token, list_id, task_id)

def todo_reopen_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    """태스크 재오픈"""
    return reopen_task(token, list_id, task_id)

def todo_snooze_task(token: str, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> Dict[str, Any]:
    """태스크 미루기"""
    return snooze_task(token, list_id, task_id, remind_at_iso, tz)

def todo_batch_get_tasks(token: str, list_id: str, task_ids: list) -> Dict[str, Any]:
    """여러 태스크 일괄 조회"""
    return batch_get_tasks(token, list_id, task_ids)

def todo_get_task_select(
    token: str,
    list_id: str,
    task_id: str,
    select: Optional[List[str]] = None,
    expand: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """특정 필드만 조회"""
    return get_task_select(token, list_id, task_id, select=select, expand=expand)

def todo_list_tasks_lite(token: str, list_id: str, top: int = 20) -> Dict[str, Any]:
    """경량 태스크 목록 조회"""
    return list_tasks_lite(token, list_id, top)

def todo_list_tasks_all_lite(token: str, list_id: str, page_size: int = 100) -> Dict[str, Any]:
    """경량 태스크 전체 조회"""
    return list_tasks_all_lite(token, list_id, page_size)

def todo_complete_task_lite(token: str, list_id: str, task_id: str) -> str:
    """경량 태스크 완료"""
    return complete_task_lite(token, list_id, task_id)

def todo_snooze_task_lite(token: str, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> str:
    """경량 태스크 미루기"""
    return snooze_task_lite(token, list_id, task_id, remind_at_iso, tz)

def todo_walk_delta_tasks_lite(token: str, list_id: str, delta_link: str = None) -> Dict[str, Any]:
    """경량 태스크 델타 전체 순회"""
    return walk_delta_tasks_lite(token, list_id, delta_link)

# -----------------------------
# 간단 파사드
# -----------------------------
def todo_list(token: str) -> Dict[str, Any]:
    """모든 리스트 조회 파사드"""
    return list_lists(token)

def todo_task(token: str, list_id: str, top: int = 10) -> Dict[str, Any]:
    """특정 리스트의 태스크 조회 파사드"""
    return list_tasks(token, list_id, top=top)

def todo_create_list(token: str, name: str) -> Dict[str, Any]:
    """리스트 생성 파사드"""
    return create_list(token, name)

def todo_create_task(token: str, list_id: str, title: str, **kwargs) -> Dict[str, Any]:
    """태스크 생성 파사드"""
    return create_task(token, list_id, title, **kwargs)

def todo_delete_list(token: str, list_id: str) -> Dict[str, Any]:
    """리스트 삭제 파사드"""
    return delete_list(token, list_id)

# -----------------------------
# HTTP 래퍼
# -----------------------------
def _request(method: Callable, url: str, token: str, *, max_retries: int = 2, **kwargs) -> Dict[str, Any]:
    """429/5xx 백오프 + 율제한 + 회로차단 + 축약 에러 표준화"""
    _circuit.before()
    _rate_limiter.acquire()
    headers = _headers(token)
    if "headers" in kwargs:
        headers.update(kwargs["headers"])
        kwargs.pop("headers")
    backoff = 0.8
    try:
        for attempt in range(max_retries + 1):
            with httpx.Client(timeout=30) as c:
                r = method(c, url, headers=headers, **kwargs)
            if r.status_code < 400:
                _circuit.record(True)
                # 일부 204(DELETE 등) 대응
                return r.json() if r.content else {}
            # 오류 축약 파싱
            try:
                err = r.json().get("error", {})
                code = err.get("code") or "Error"
                msg = err.get("message") or r.text
            except Exception:
                code, msg = "Error", r.text[:120]
            # 재시도 대상
            if r.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            _circuit.record(False)
            raise GraphAPIError(r.status_code, code, (msg or "")[:120])
    except GraphAPIError:
        raise
    except Exception as e:
        _circuit.record(False)
        raise GraphAPIError(500, "Client", str(e)[:120])

def _iso(dt: datetime) -> str:
    """datetime → ISO(UTC) 문자열(마이크로초 제거).
    naive datetime이 들어오면 UTC로 간주."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()

def _project_task(item: Dict[str, Any]) -> Dict[str, Any]:
    """태스크 최소 필드 투영(Lite 응답)"""
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "status": item.get("status"),
        "due": (item.get("dueDateTime") or {}).get("dateTime"),
        "remind": (item.get("reminderDateTime") or {}).get("dateTime"),
        "importance": item.get("importance"),
    }

Importance = Literal["low", "normal", "high"]
Status = Literal["notStarted", "inProgress", "completed", "waitingOnOthers", "deferred"]

# -----------------------------
# 리스트
# -----------------------------
def list_lists(token: str) -> Dict[str, Any]:
    try:
        return _request(lambda c, u, **kw: c.get(u, **kw), f"{GRAPH}/me/todo/lists", token)
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def create_list(token: str, display_name: str) -> Dict[str, Any]:
    body = {"displayName": display_name}
    try:
        return _request(lambda c, u, **kw: c.post(u, json=body, **kw), f"{GRAPH}/me/todo/lists", token)
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def update_list(token: str, list_id: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if display_name is not None:
        patch["displayName"] = display_name
    try:
        return _request(lambda c, u, **kw: c.patch(u, json=patch, **kw), f"{GRAPH}/me/todo/lists/{list_id}", token)
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def delete_list(token: str, list_id: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, **kw), f"{GRAPH}/me/todo/lists/{list_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

# -----------------------------
# 태스크 (코어)
# -----------------------------
def list_tasks(token: str, list_id: str, filter_expr: Optional[str] = None, top: Optional[int] = None) -> Dict[str, Any]:
    params: Dict[str, str] = {}
    if filter_expr:
        params["$filter"] = filter_expr
    if top:
        params["$top"] = str(top)
    try:
        return _request(lambda c, u, **kw: c.get(u, params=params, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks", token)
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def list_tasks_all(token: str, list_id: str, filter_expr: Optional[str] = None, page_size: int = 100) -> Iterator[Dict[str, Any]]:
    """@odata.nextLink 자동 추적 제너레이터"""
    params: Dict[str, str] = {}
    if filter_expr:
        params["$filter"] = filter_expr
    if page_size:
        params["$top"] = str(page_size)

    url = f"{GRAPH}/me/todo/lists/{list_id}/tasks"
    while True:
        data = _request(lambda c, u, **kw: c.get(u, params=params if u == url else None, **kw), url, token)
        items = data.get("value", []) or []
        for it in items:
            yield it
        next_link = data.get("@odata.nextLink")
        if not next_link:
            break
        url = next_link

def get_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    return _request(lambda c, u, **kw: c.get(u, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", token)

def create_task(
    token: str,
    list_id: str,
    title: str,
    body: Optional[str] = None,
    due: Optional[str] = None,
    time_zone: Optional[str] = "Asia/Seoul",
    reminder: Optional[str] = None,
    importance: Optional[Importance] = None,
    status: Optional[Status] = None,
    recurrence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"title": title}
    if body:
        payload["body"] = {"content": body, "contentType": "text"}
    if due:
        payload["dueDateTime"] = {"dateTime": due, "timeZone": time_zone or "UTC"}
    if reminder:
        payload["reminderDateTime"] = {"dateTime": reminder, "timeZone": time_zone or "UTC"}
    if importance:
        payload["importance"] = importance
    if status:
        payload["status"] = status
    if recurrence:
        payload["recurrence"] = recurrence

    return _request(lambda c, u, **kw: c.post(u, json=payload, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks", token)

def update_task(token: str, list_id: str, task_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    return _request(lambda c, u, **kw: c.patch(u, json=patch, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", token)

def delete_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

# -----------------------------
# 델타
# -----------------------------
def delta_lists(token: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/delta"
    return _request(lambda c, u, **kw: c.get(u, **kw), url, token)

def delta_tasks(token: str, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/{list_id}/tasks/delta"
    return _request(lambda c, u, **kw: c.get(u, **kw), url, token)

def walk_delta_lists(token: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    """deltaLink/nextLink를 함께 반환해 호출자가 보관·재사용"""
    data = delta_lists(token, delta_link=delta_link)
    return {
        "value": data.get("value", []),
        "deltaLink": data.get("@odata.deltaLink") or data.get("@odata.nextLink"),
    }

def walk_delta_tasks(token: str, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    data = delta_tasks(token, list_id, delta_link=delta_link)
    return {
        "value": data.get("value", []),
        "deltaLink": data.get("@odata.deltaLink") or data.get("@odata.nextLink"),
    }

# -----------------------------
# 편의/업무 동사
# -----------------------------
def find_or_create_list(token: str, display_name: str) -> Dict[str, Any]:
    lists = list_lists(token).get("value", [])
    for li in lists:
        if li.get("displayName") == display_name:
            return li
    return create_list(token, display_name)

def quick_task(
    token: str,
    list_name: str,
    title: str,
    *,
    body: Optional[str] = None,
    due_in_days: Optional[int] = None,
    remind_in_hours: Optional[int] = None,
    importance: Optional[Importance] = None,
) -> Dict[str, Any]:
    li = find_or_create_list(token, list_name)
    due = _iso(datetime.now() + timedelta(days=due_in_days)) if due_in_days is not None else None
    reminder = _iso(datetime.now() + timedelta(hours=remind_in_hours)) if remind_in_hours is not None else None
    return create_task(
        token,
        li["id"],
        title,
        body=body,
        due=due,
        time_zone="UTC",
        reminder=reminder,
        importance=importance,
    )

def complete_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    patch = {
        "status": "completed",
        "completedDateTime": {"dateTime": _iso(datetime.utcnow()), "timeZone": "UTC"},
    }
    return update_task(token, list_id, task_id, patch)

def reopen_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    patch = {"status": "notStarted"}
    return update_task(token, list_id, task_id, patch)

def snooze_task(token: str, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> Dict[str, Any]:
    patch = {"reminderDateTime": {"dateTime": remind_at_iso, "timeZone": tz}}
    return update_task(token, list_id, task_id, patch)

# -----------------------------
# 대량/선택 쿼리
# -----------------------------
def batch_get_tasks(token: str, list_id: str, task_ids: List[str]) -> Dict[str, Any]:
    """Graph $batch(권장 20개/요청 이하)"""
    requests = []
    for i, tid in enumerate(task_ids, 1):
        requests.append({
            "id": str(i),
            "method": "GET",
            "url": f"/me/todo/lists/{list_id}/tasks/{tid}",
        })
    body = {"requests": requests}
    return _request(lambda c, u, **kw: c.post(u, json=body, **kw), f"{GRAPH}/$batch", token)

def get_task_select(
    token: str,
    list_id: str,
    task_id: str,
    select: Optional[List[str]] = None,
    expand: Optional[List[str]] = None,
) -> Dict[str, Any]:
    params: Dict[str, str] = {}
    if select:
        params["$select"] = ",".join(select)
    if expand:
        params["$expand"] = ",".join(expand)
    url = f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}"
    return _request(lambda c, u, **kw: c.get(u, params=params, **kw), url, token)

# -----------------------------
# LLM-Lite 파사드(짧은 I/O)
# -----------------------------
def quick_task_lite(
    token: str,
    list_name: str,
    title: str,
    *,
    body: Optional[str] = None,
    due_in_days: Optional[int] = None,
    remind_in_hours: Optional[int] = None,
    importance: Importance = "normal",
) -> str:
    """성공: 'ok:<task_id>'"""
    li = find_or_create_list(token, list_name)
    due = _iso(datetime.now() + timedelta(days=due_in_days)) if due_in_days is not None else None
    reminder = _iso(datetime.now() + timedelta(hours=remind_in_hours)) if remind_in_hours is not None else None
    created = create_task(
        token,
        li["id"],
        title,
        body=body,
        due=due,
        time_zone="UTC",
        reminder=reminder,
        importance=importance,
    )
    return f"ok:{created.get('id')}"

def list_tasks_lite(token: str, list_id: str, top: int = 20) -> Dict[str, Any]:
    params = {
        "$select": "id,title,status,dueDateTime,reminderDateTime,importance",
        "$top": str(top),
    }
    data = _request(lambda c, u, **kw: c.get(u, params=params, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks", token)
    items = [_project_task(x) for x in data.get("value", [])]
    return {"items": items, "next": data.get("@odata.nextLink")}

def list_tasks_all_lite(token: str, list_id: str, page_size: int = 100) -> Dict[str, Any]:
    params = {
        "$select": "id,title,status,dueDateTime,reminderDateTime,importance",
        "$top": str(page_size),
    }
    url = f"{GRAPH}/me/todo/lists/{list_id}/tasks"
    out: List[Dict[str, Any]] = []
    while True:
        data = _request(lambda c, u, **kw: c.get(u, params=params if u == url else None, **kw), url, token)
        out.extend(_project_task(x) for x in data.get("value", []) or [])
        nxt = data.get("@odata.nextLink")
        if not nxt:
            break
        url = nxt
    return {"items": out}

def complete_task_lite(token: str, list_id: str, task_id: str) -> str:
    patch = {"status": "completed", "completedDateTime": {"dateTime": _iso(datetime.utcnow()), "timeZone": "UTC"}}
    _ = update_task(token, list_id, task_id, patch)
    return "ok"

def snooze_task_lite(token: str, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> str:
    _ = update_task(token, list_id, task_id, {"reminderDateTime": {"dateTime": remind_at_iso, "timeZone": tz}})
    return "ok"

def walk_delta_tasks_lite(token: str, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    data = delta_tasks(token, list_id, delta_link=delta_link)
    items = [_project_task(x) for x in data.get("value", []) or []]
    return {"items": items, "delta": data.get("@odata.deltaLink") or data.get("@odata.nextLink")}
