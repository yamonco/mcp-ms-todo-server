# adapter_graph_rest.py (2025 MCP structure)
# - Microsoft Graph API integration adapter
# - REST calls based on access token, includes error/rate limiter/circuit breaker utilities

import os, time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Callable, Iterator, Literal, List

import httpx
from app.config import cfg

GRAPH = cfg.graph_base_url


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

    def before(self) -> None:
        with self.lock:
            now = time.time()
            if now < self.open_until:
                raise GraphAPIError(503, "CircuitOpen", "circuit open")

    def record(self, ok: bool) -> None:
        with self.lock:
            if ok:
                self.fail = 0
            else:
                self.fail += 1
                if self.fail >= self.fail_threshold:
                    self.open_until = time.time() + self.cooldown_sec


_rate_limiter = _RateLimiter(rate_per_sec=cfg.rate_per_sec, burst=cfg.rate_burst)
_circuit = _CircuitBreaker(fail_threshold=cfg.cb_fails, cooldown_sec=cfg.cb_cooldown_sec)
_HTTPX = httpx.Client(timeout=cfg.http_timeout)

# -----------------------------
# Simple Facade helpers (kept minimal)
# -----------------------------

# -----------------------------
# HTTP Wrapper
# -----------------------------
def _parse_retry_after(val: str) -> float:
    """Parse Retry-After header (seconds or HTTP-date). Return seconds to sleep (>=0)."""
    try:
        s = float(val)
        return max(0.0, s)
    except Exception:
        pass
    # HTTP-date
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(val)
        return max(0.0, (dt - datetime.utcnow().replace(tzinfo=dt.tzinfo)).total_seconds())
    except Exception:
        return 0.0


def _request(method: Callable, url: str, token: str, *, max_retries: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """429/5xx backoff + rate limit + circuit breaker + standardized error handling
    - Honors Retry-After header when present
    - max_retries uses env (default 2) when None
    """
    _circuit.before()
    _rate_limiter.acquire()

    headers = _headers(token)
    if "headers" in kwargs:
        headers.update(kwargs["headers"])
        kwargs.pop("headers")

    retries = int(os.getenv("HTTP_MAX_RETRIES", "2")) if max_retries is None else max_retries
    backoff = float(os.getenv("HTTP_BACKOFF_INITIAL", "0.8"))
    backoff_factor = float(os.getenv("HTTP_BACKOFF_FACTOR", "2.0"))

    for attempt in range(retries + 1):
        try:
            r = method(_HTTPX, url, headers=headers, **kwargs)
        except Exception as e:
            _circuit.record(False)
            raise GraphAPIError(500, "Client", str(e)[:120])

        if r.status_code < 400:
            _circuit.record(True)
            return r.json() if r.content else {}

        try:
            err = r.json().get("error", {})
            code = err.get("code") or "Error"
            msg = err.get("message") or r.text
        except Exception:
            code, msg = "Error", r.text[:120]

        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            ra = r.headers.get("Retry-After")
            wait = _parse_retry_after(ra) if ra else backoff
            time.sleep(max(0.0, wait))
            backoff *= backoff_factor
            continue

        _circuit.record(False)
        raise GraphAPIError(r.status_code, code, (msg or "")[:120])

# -----------------------------
# Common Utilities
# -----------------------------
def _iso(dt: datetime) -> str:
    """datetime → ISO(UTC) string (microseconds removed).
    If naive datetime is given, assume UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _project_task(item: Dict[str, Any]) -> Dict[str, Any]:
    """Project minimal fields for task (Lite response)"""
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
# List (Core)
# -----------------------------
def list_lists(token: str) -> Dict[str, Any]:
    return _request(lambda c, u, **kw: c.get(u, **kw), f"{GRAPH}/me/todo/lists", token)


def create_list(token: str, name: str) -> Dict[str, Any]:
    body = {"displayName": name}
    return _request(lambda c, u, **kw: c.post(u, json=body, **kw), f"{GRAPH}/me/todo/lists", token)


def update_list(token: str, list_id: str, display_name: str) -> Dict[str, Any]:
    body = {"displayName": display_name}
    return _request(lambda c, u, **kw: c.patch(u, json=body, **kw), f"{GRAPH}/me/todo/lists/{list_id}", token)


def delete_list(token: str, list_id: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, **kw), f"{GRAPH}/me/todo/lists/{list_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def delete_list_if_match(token: str, list_id: str, etag: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, headers={"If-Match": etag}, **kw), f"{GRAPH}/me/todo/lists/{list_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

# -----------------------------
# Task (Core)
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
    """@odata.nextLink auto-follow generator"""
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

def update_task_if_match(token: str, list_id: str, task_id: str, patch: Dict[str, Any], etag: str) -> Dict[str, Any]:
    return _request(
        lambda c, u, **kw: c.patch(u, json=patch, headers={"If-Match": etag}, **kw),
        f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}",
        token,
    )


def delete_task(token: str, list_id: str, task_id: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

def delete_task_if_match(token: str, list_id: str, task_id: str, etag: str) -> Dict[str, Any]:
    try:
        _request(lambda c, u, **kw: c.delete(u, headers={"If-Match": etag}, **kw), f"{GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}", token)
        return {"success": True}
    except GraphAPIError as e:
        return {"error": str(e), "code": e.code, "status": e.status}

# -----------------------------
# Delta
# -----------------------------
def delta_lists(token: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/delta"
    return _request(lambda c, u, **kw: c.get(u, **kw), url, token)


def delta_tasks(token: str, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    url = delta_link or f"{GRAPH}/me/todo/lists/{list_id}/tasks/delta"
    return _request(lambda c, u, **kw: c.get(u, **kw), url, token)


def walk_delta_lists(token: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
    """Returns both deltaLink/nextLink for caller to store and reuse"""
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
# Convenience/Business Verbs
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
# Bulk/Selective Query
# -----------------------------
def batch_get_tasks(token: str, list_id: str, task_ids: List[str]) -> Dict[str, Any]:
    """Graph $batch (Recommended: 20 items/request or less)"""
    requests = []
    for i, tid in enumerate(task_ids, 1):
        requests.append({
            "id": str(i),
            "method": "GET",
            "url": f"/me/todo/lists/{list_id}/tasks/{tid}",
        })
    body = {"requests": requests}
    return _request(lambda c, u, **kw: c.post(u, json=body, **kw), f"{GRAPH}/$batch", token)

def batch_get_tasks_chunked(token: str, list_id: str, task_ids: List[str], *, chunk_size: int = 20) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    for i in range(0, len(task_ids), chunk_size):
        chunk = task_ids[i:i+chunk_size]
        res = batch_get_tasks(token, list_id, chunk)
        out.extend(res.get("responses", []))
    return {"responses": out}


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
# LLM-Lite Facade (Short I/O)
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
    """Success: 'ok:<task_id>'"""
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
