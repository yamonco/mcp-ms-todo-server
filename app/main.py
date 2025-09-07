 # main.py (2025 MCP latest structure)
 # - FastAPI-based MCP server
 # - All features are provided via a single JSON-RPC endpoint (/mcp) using tools/list, tools/call
 # - Service layer (TodoService) handles Graph API integration and business logic

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
from collections import defaultdict

from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from app.tools import _list_tools, _call_tool
from app.apikeys import (
    generate_api_key,
    list_keys as apikey_list,
    delete_key as apikey_delete,
    resolve_key,
    list_users as apikey_users,
    update_key as apikey_update,
)
from app import rbac
from app.tokens import list_tokens as token_list, upsert_token as token_upsert, get_token_by_profile
from app.context import set_current_user_meta
from app.config import cfg


 # Logging setup
logger = logging.getLogger("mcp")
logging.basicConfig(level=getattr(logging, cfg.log_level))

# Optional Sentry setup (if installed and DSN provided)
try:
    if os.getenv("SENTRY_DSN"):
        import sentry_sdk  # type: ignore
        try:
            from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore
            sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), integrations=[FastApiIntegration()])
        except Exception:
            sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
except Exception:
    pass


 # MCP server meta/capabilities
MCP_JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_REV = cfg.protocol_revision  # Latest MCP revision

CAPABILITIES = {
    "capabilities": {"tools": {"listChanged": False}},
    "protocolRevision": MCP_PROTOCOL_REV,
    "server": {"name": cfg.server_name, "version": cfg.server_version},
}

# (domain helpers removed; tool execution is handled in app.tools)

# ---------------------------------------------------------------------
# JSON-RPC 2.0 Model/Helper
# ---------------------------------------------------------------------
class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field(MCP_JSONRPC_VERSION)
    method: str
    id: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None

def _jsonrpc_ok(id_val: Any, result: Dict[str, Any], *, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": id_val, "result": result}, headers=headers or {})

def _jsonrpc_err(id_val: Any, code: int, message: str, *, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": id_val, "error": {"code": code, "message": message}}, headers=headers or {})

# (tool output wrapping handled in app.tools; keep server minimal)

# ---------------------------------------------------------------------
# FastAPI 앱
# ---------------------------------------------------------------------



app = FastAPI(title=cfg.server_name, version=cfg.server_version)
try:
    # 개발 편의: DB_URL 미지정 시 SQLite 기본값으로 폴백
    if not cfg.db_url:
        os.environ["DB_URL"] = "sqlite:///./secrets/app.db"
        from importlib import reload as _reload
        from app import config as _cfgmod
        _reload(_cfgmod)  # cfg 갱신
    # 스키마 자동 생성(개발 편의). 운영은 Alembic 권장.
    from app.models import Base
    from app.db import ensure_schema
    ensure_schema(Base)
except Exception:
    pass
@app.get("/mcp/manifest")
def mcp_manifest(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None), request: Request = None):
    """
    MCP 툴 선언 manifest를 JSON으로 반환 (Cursor 등에서 자동 임포트 가능)
    """
    # 베스트 에포트로 키를 확인해 컨텍스트를 세팅(실패해도 전체 노출)
    try:
        require_api_key(request, x_api_key, authorization)
    except HTTPException:
        pass
    tools, _ = _list_tools(None)
    return {"tools": tools}

# SSE client registry (simple fan-out)
_sse_clients: set[asyncio.Queue[str]] = set()

# Simple in-memory metrics (Prometheus exposition)
_metrics = defaultdict(int)
_metrics_sum = defaultdict(float)
_metrics_count = defaultdict(int)
_hist_buckets = defaultdict(int)

def _mkey(name: str, labels: Dict[str, str]) -> tuple:
    return (name, tuple(sorted(labels.items())))

def _inc(name: str, **labels: str) -> None:
    _metrics[_mkey(name, labels)] += 1

def _observe(name: str, value: float, **labels: str) -> None:
    key = _mkey(name, labels)
    _metrics_sum[key] += float(value)
    _metrics_count[key] += 1

# Histogram support (Prometheus exposition)
_HIST_BUCKETS_MS = [5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]

def _observe_hist(name: str, value_ms: float, **labels: str) -> None:
    v = float(value_ms)
    # Update sum/count
    _observe(name, v, **labels)
    # Increment buckets (cumulative semantics)
    for b in _HIST_BUCKETS_MS:
        if v <= b:
            key = (name, tuple(sorted(labels.items())), str(b))
            _hist_buckets[key] += 1
    # +Inf bucket
    key_inf = (name, tuple(sorted(labels.items())), "+Inf")
    _hist_buckets[key_inf] += 1

def _render_metrics() -> str:
    lines = []
    # Counters
    counters = {
        "mcp_requests_total": "Total MCP requests",
        "mcp_auth_total": "Auth attempts",
    }
    for metric, help_text in counters.items():
        lines.append(f"# HELP {metric} {help_text}")
        lines.append(f"# TYPE {metric} counter")
        for (name, label_pairs), val in _metrics.items():
            if name != metric:
                continue
            label_str = ",".join([f'{k}="{v}"' for k, v in label_pairs])
            lines.append(f"{name}{{{label_str}}} {val}")

    # Gauges
    lines.append("# HELP mcp_sse_connections Current SSE connections")
    lines.append("# TYPE mcp_sse_connections gauge")
    lines.append(f"mcp_sse_connections {len(_sse_clients)}")

    # Summaries (sum/count pairs)
    lines.append("# HELP mcp_tool_duration_ms Tool call duration in milliseconds (summary)")
    lines.append("# TYPE mcp_tool_duration_ms summary")
    for (name, label_pairs), s in _metrics_sum.items():
        if name != "mcp_tool_duration_ms":
            continue
        c = _metrics_count.get((name, label_pairs), 0)
        label_str = ",".join([f'{k}="{v}"' for k, v in label_pairs])
        lines.append(f"{name}_sum{{{label_str}}} {s}")
        lines.append(f"{name}_count{{{label_str}}} {c}")

    # Histograms
    def render_hist(name: str, help_text: str):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} histogram")
        # Group by labels (excluding 'le')
        groups = {}
        for (mname, label_pairs, le), cnt in _hist_buckets.items():
            if mname != name:
                continue
            groups.setdefault(tuple(label_pairs), []).append((le, cnt))
        for label_pairs, items in groups.items():
            # Ensure all buckets present
            buckets = {le: cnt for le, cnt in items}
            ordered = [(str(b), buckets.get(str(b), 0)) for b in _HIST_BUCKETS_MS] + [("+Inf", buckets.get("+Inf", 0))]
            base_labels = dict(label_pairs)
            for le, cnt in ordered:
                lbl = dict(base_labels)
                lbl["le"] = le
                label_str = ",".join([f'{k}="{v}"' for k, v in sorted(lbl.items())])
                lines.append(f"{name}_bucket{{{label_str}}} {cnt}")
            # sum/count
            s = _metrics_sum.get((name, label_pairs), 0.0)
            c = _metrics_count.get((name, label_pairs), 0)
            label_str = ",".join([f'{k}="{v}"' for k, v in label_pairs])
            lines.append(f"{name}_sum{{{label_str}}} {s}")
            lines.append(f"{name}_count{{{label_str}}} {c}")

    render_hist("mcp_http_request_duration_ms", "HTTP request latency by endpoint/status/tool")
    render_hist("mcp_tool_call_duration_ms", "Tool call latency by tool")
    return "\n".join(lines) + "\n"

@app.get("/mcp")
async def mcp_sse(request: Request, x_api_key: str = Header(None), authorization: str = Header(None)):
    """Optional SSE stream for clients that open a separate event channel.
    We broadcast JSON-RPC responses as SSE data frames on this channel.
    """
    accept = request.headers.get("accept", "")
    # Lightweight auth for GET (both SSE and non-SSE).
    # Accept credentials via X-API-Key header, Authorization: Bearer, or query param ?x-api-key=..
    if cfg.api_key:
        provided = _get_provided_key(request, x_api_key, authorization)
        if not provided or provided != cfg.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API Key")

    if "text/event-stream" not in accept:
        # For non-SSE GET, return capabilities quickly
        return JSONResponse({"server": CAPABILITIES["server"], "protocolRevision": MCP_PROTOCOL_REV})

    q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _sse_clients.add(q)

    async def event_gen():
        try:
            # Initial hello
            yield f": keep-alive\n\n"
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {item}\n\n"
                except asyncio.TimeoutError:
                    # keep alive comment
                    yield f": ping\n\n"
                    continue
        finally:
            _sse_clients.discard(q)

    return StreamingResponse(event_gen(), media_type="text/event-stream")

# CORS 제한: 모든 Origin 차단 (필요시 특정 도메인만 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allow_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600,
)

# API Key 인증 미들웨어
EXPECTED_API_KEY = cfg.api_key

def _get_provided_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    # Priority: X-API-Key header -> Authorization(Bearer/Basic) -> Cookie -> query param (?x-api-key|?api_key|?apikey)
    if x_api_key:
        return x_api_key
    if authorization:
        lower = authorization.lower()
        if lower.startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        if lower.startswith("basic "):
            # Accept Basic user:pass, we take pass as api key
            import base64
            try:
                raw = authorization.split(" ", 1)[1].strip()
                dec = base64.b64decode(raw).decode("utf-8", "ignore")
                if ":" in dec:
                    return dec.split(":", 1)[1]
            except Exception:
                pass
    # Cookie lookup
    try:
        ck = request.cookies.get("x-api-key") or request.cookies.get("api_key") or request.cookies.get("apikey")
        if ck:
            return ck
    except Exception:
        pass
    qp = request.query_params.get("x-api-key")
    if qp:
        return qp
    qp = request.query_params.get("api_key") or request.query_params.get("apikey")
    if qp:
        return qp
    return None

def require_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]):
    provided = _get_provided_key(request, x_api_key, authorization)
    # Master key short-circuit
    if EXPECTED_API_KEY and provided == EXPECTED_API_KEY:
        _inc("mcp_auth_total", outcome="success", kind="master")
        set_current_user_meta({"master": True})
        return
    # Generated key path
    ok, meta = resolve_key(provided)
    if ok:
        _inc("mcp_auth_total", outcome="success", kind="key")
        set_current_user_meta(meta or None)
        return
    # If neither master nor generated keys are configured, allow open (dev mode)
    has_any_keys = bool(EXPECTED_API_KEY) or bool(apikey_list())
    if not has_any_keys:
        _inc("mcp_auth_total", outcome="success", kind="open")
        set_current_user_meta(None)
        return
    _inc("mcp_auth_total", outcome="failure")
    raise HTTPException(status_code=401, detail="Invalid or missing API Key")


def _allowed_tools_for_request(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> Optional[set[str]]:
    provided = _get_provided_key(request, x_api_key, authorization)
    # Master key → all tools
    if EXPECTED_API_KEY and provided == EXPECTED_API_KEY:
        return None
    ok, meta = resolve_key(provided)
    if not ok:
        # No keys configured → open; else None means all, here return None only if no keys configured
        has_any_keys = bool(EXPECTED_API_KEY) or bool(apikey_list())
        return None if not has_any_keys else set()
    names = set((meta or {}).get("allowed_tools", []) or [])
    return names


@app.get("/health")
def health(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    require_api_key(request, x_api_key, authorization)
    return {
        "status": "ok",
        "server": CAPABILITIES["server"],
        "protocolRevision": MCP_PROTOCOL_REV,
        "apiKeyRequired": bool(cfg.api_key),
        "tokenPresent": True,  # DB 기반으로 관리
    }

@app.get("/mcp/capabilities")
def mcp_capabilities():
    # 서버 능력 공개(스펙: tools capability 선언)
    # TODO: MCP 최신 스펙 변화 시 server/capabilities notification 고려
    return CAPABILITIES



@app.post("/mcp")
async def mcp_entry(request: Request, x_api_key: str = Header(None), authorization: str = Header(None)):
    # API Key 인증 (X-API-Key / Authorization: Bearer / query param)
    require_api_key(request, x_api_key, authorization)
    """
    단일 JSON-RPC 엔드포인트 (SSE/HTTP 자동 분기)
    """
    accept = request.headers.get("accept", "")

    import time
    t0 = time.time()
    try:
        payload = await request.json()
    except Exception:
        return _jsonrpc_err(None, -32700, "Parse error")

    if isinstance(payload, list):
        return _jsonrpc_err(None, -32600, "Batch not supported")

    try:
        req = JsonRpcRequest.model_validate(payload)
    except ValidationError:
        return _jsonrpc_err(None, -32600, "Invalid Request")

    if req.jsonrpc != MCP_JSONRPC_VERSION:
        return _jsonrpc_err(req.id, -32600, "Invalid jsonrpc version")

    method = req.method or ""
    params = req.params or {}

    # JSON-RPC notifications (no id): acknowledge without body
    # Common notifications include 'notifications/initialized'
    if req.id is None:
        logger.info(json.dumps({"event": "notification", "method": method}))
        # Some clients warn on 204; return empty JSON 200 to be lenient
        return FastAPIJSONResponse(content={})

    # Some clients may send notifications with an id (non-standard).
    # For methods under notifications/*, return empty success to avoid warnings.
    if isinstance(method, str) and method.startswith("notifications/"):
        return _jsonrpc_ok(req.id, {})

    # Compatibility shim: allow calling tool name directly as JSON-RPC method
    # e.g., method="todo.lists.get" with params={} → tools/call {name, arguments}
    if method not in ("initialize", "tools/list", "tools/call"):
        if isinstance(params, dict):
            method = "tools/call"
            params = {"name": req.method, "arguments": params}
        else:
            return _jsonrpc_err(req.id, -32602, "Invalid params")
    correlation_id = request.headers.get("x-correlation-id") or str(req.id) or "-"

    def log_event(event: str, **fields):
        try:
            msg = {"event": event, "id": req.id, "method": method, "corr": correlation_id}
            msg.update(fields)
            logger.info(json.dumps(msg, ensure_ascii=False))
        except Exception:
            logger.info(f"{event} id={req.id} method={method} corr={correlation_id} {fields}")

    # initialize/tools/list는 항상 JSON 응답
    # SSE는 tools/call에서만 허용 (Accept: text/event-stream)
    is_sse = cfg.sse_enabled and (method == "tools/call") and ("text/event-stream" in accept)

    # SSE 스트리밍 응답 핸들러
    async def sse_stream():
        import asyncio
        # SSE는 tools/call에서만 사용
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not name or not isinstance(arguments, dict):
                msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32602, "message": "Invalid params"}})
                yield f"data: {msg}\n\n"
                return
            try:
                # 진행 로그 예시: 툴 실행 시작
                log_event("tool.start", tool=name)
                yield f"data: {json.dumps({'event': 'start', 'tool': name, 'corr': correlation_id})}\n\n"
                # 실제 툴 실행 (비동기 sleep으로 진행 로그 시뮬레이션)
                # 실서비스에서는 yield로 중간 로그/상태를 전송
                result = _call_tool(name, arguments)
                # 툴 실행 완료
                log_event("tool.finish", tool=name)
                yield f"data: {json.dumps({'event': 'finish', 'tool': name, 'corr': correlation_id})}\n\n"
                # 최종 결과
                msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result})
                yield f"data: {msg}\n\n"
            except TypeError as te:
                msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32602, "message": f"Invalid params: {str(te)}"}})
                yield f"data: {msg}\n\n"
            except Exception as e:
                logger.exception("server error on tools/call (SSE)")
                msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32000, "message": f"Server error: {str(e)}"}})
                yield f"data: {msg}\n\n"
            return
        # 그 외는 JSON으로만 응답하도록 처리
        msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32601, "message": "Method not found"}})
        yield f"data: {msg}\n\n"
        return

    # SSE 분기
    if is_sse:
        return StreamingResponse(sse_stream(), media_type="text/event-stream")

    # 기존 HTTP 응답
    # -------------------------
    # initialize (capabilities, serverInfo, protocolRevision)
    # -------------------------
    if method == "initialize":
        log_event("rpc", stage="initialize")
        _inc("mcp_requests_total", method="initialize", status="ok")
        _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="initialize", status="ok", tool="")
        resp = {
            "capabilities": CAPABILITIES["capabilities"],
            "server": CAPABILITIES["server"],
            "protocolRevision": MCP_PROTOCOL_REV
        }
        # broadcast to SSE listeners as well
        try:
            payload = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": resp})
            for q in list(_sse_clients):
                q.put_nowait(payload)
        except Exception:
            pass
        return _jsonrpc_ok(req.id, resp, headers={"x-correlation-id": correlation_id})

    # -------------------------
    # tools/list
    # -------------------------
    if method == "tools/list":
        cursor = params.get("cursor")
        tools, next_cursor = _list_tools(cursor)
        allowed = _allowed_tools_for_request(request, x_api_key, authorization)
        if allowed is not None:
            tools = [t for t in tools if t.get("name") in allowed]
        result = {"tools": tools}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        log_event("rpc", stage="tools/list")
        _inc("mcp_requests_total", method="tools/list", status="ok")
        _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/list", status="ok", tool="")
        try:
            payload = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result})
            for q in list(_sse_clients):
                q.put_nowait(payload)
        except Exception:
            pass
        return _jsonrpc_ok(req.id, result, headers={"x-correlation-id": correlation_id})

    # -------------------------
    # tools/call
    # -------------------------
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not name or not isinstance(arguments, dict):
            log_event("rpc.error", reason="invalid_params")
            _inc("mcp_requests_total", method="tools/call", tool=name or "", status="invalid_params")
            _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/call", status="invalid_params", tool=name or "")
            return _jsonrpc_err(req.id, -32602, "Invalid params", headers={"x-correlation-id": correlation_id})
        allowed = _allowed_tools_for_request(request, x_api_key, authorization)
        if allowed is not None and name not in allowed:
            _inc("mcp_requests_total", method="tools/call", tool=name, status="forbidden")
            _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/call", status="forbidden", tool=name)
            return _jsonrpc_err(req.id, -32601, "Tool not allowed for this API key", headers={"x-correlation-id": correlation_id})
        try:
            result = _call_tool(name, arguments)
            dt = int((time.time() - t0) * 1000)
            log_event("rpc", stage="tools/call", tool=name, ms=dt)
            _inc("mcp_requests_total", method="tools/call", tool=name, status="ok")
            _observe("mcp_tool_duration_ms", dt, tool=name)
            _observe_hist("mcp_tool_call_duration_ms", dt, tool=name)
            _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/call", status="ok", tool=name)
            # broadcast to SSE listeners as well
            try:
                payload = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result})
                for q in list(_sse_clients):
                    q.put_nowait(payload)
            except Exception:
                pass
            return _jsonrpc_ok(req.id, result, headers={"x-correlation-id": correlation_id})
        except TypeError as te:
            log_event("rpc.error", tool=name, reason="type_error", msg=str(te))
            _inc("mcp_requests_total", method="tools/call", tool=name, status="type_error")
            _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/call", status="type_error", tool=name)
            return _jsonrpc_err(req.id, -32602, f"Invalid params: {str(te)}", headers={"x-correlation-id": correlation_id})
        except Exception as e:
            logger.exception("server error on tools/call")
            log_event("rpc.error", tool=name, reason="server_error", msg=str(e))
            _inc("mcp_requests_total", method="tools/call", tool=name, status="server_error")
            _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint="tools/call", status="server_error", tool=name)
            return _jsonrpc_err(req.id, -32000, f"Server error: {str(e)}", headers={"x-correlation-id": correlation_id})

    log_event("rpc.error", reason="method_not_found")
    _observe_hist("mcp_http_request_duration_ms", int((time.time() - t0) * 1000), endpoint=method, status="not_found", tool="")
    return _jsonrpc_err(req.id, -32601, "Method not found", headers={"x-correlation-id": correlation_id})

# ---------------------------------------------------------------------
# Admin: API key management (master key only)
# ---------------------------------------------------------------------
class CreateKeyPayload(BaseModel):
    template: str
    allowed_tools: Optional[list[str]] = None
    note: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    role: Optional[str] = None


def _require_master(request: Request, x_api_key: Optional[str], authorization: Optional[str]):
    provided = _get_provided_key(request, x_api_key, authorization)
    # Dev-open mode: if no master and no generated keys exist, allow
    try:
        has_any_keys = bool(EXPECTED_API_KEY) or bool(apikey_list())
    except Exception:
        has_any_keys = bool(EXPECTED_API_KEY)
    if not has_any_keys:
        return
    if EXPECTED_API_KEY and provided == EXPECTED_API_KEY:
        return
    raise HTTPException(status_code=403, detail="Master API key required")


@app.post("/admin/api-keys")
def create_api_key(payload: CreateKeyPayload, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    key, meta = generate_api_key(
        payload.template,
        allowed_tools=payload.allowed_tools,
        note=payload.note,
        user_id=payload.user_id,
        name=payload.name,
        token_profile=payload.token_profile,
        token_id=payload.token_id,
        role=payload.role,
    )
    return {"api_key": key, "meta": meta}


@app.get("/admin/api-keys")
def list_api_keys(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    return apikey_list()


@app.delete("/admin/api-keys/{key}")
def delete_api_key(key: str, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    ok = apikey_delete(key)
    if not ok:
        raise HTTPException(status_code=404, detail="key not found")
    return {"deleted": True}


class UpdateKeyPayload(BaseModel):
    template: Optional[str] = None
    allowed_tools: Optional[list[str]] = None
    note: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    role: Optional[str] = None


# Tokens management (admin)
class UpsertTokenPayload(BaseModel):
    profile: Optional[str] = None
    token: Dict[str, Any]
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None


@app.patch("/admin/api-keys/{key}")
def update_api_key(key: str, payload: UpdateKeyPayload, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    meta = apikey_update(key, payload.model_dump())
    if not meta:
        raise HTTPException(status_code=404, detail="key not found")
    return {"api_key": key, "meta": meta}


@app.get("/admin/tokens")
def list_tokens(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    return token_list()


@app.post("/admin/tokens")
def upsert_token(payload: UpsertTokenPayload, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    res = token_upsert(
        profile=payload.profile,
        token_data=payload.token,
        tenant_id=payload.tenant_id,
        client_id=payload.client_id,
        scopes=payload.scopes,
    )
    return res


@app.get("/admin/tokens/by-profile/{profile}")
def read_token_by_profile(profile: str, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    data = get_token_by_profile(profile)
    if not data:
        raise HTTPException(status_code=404, detail="token not found")
    return data


@app.post("/admin/users")
def create_user(payload: CreateKeyPayload, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    return create_api_key(payload, request, x_api_key, authorization)


@app.get("/admin/users")
def list_users(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    return apikey_users()


# RBAC role management (admin)
class RolePayload(BaseModel):
    tools: list[str]


@app.get("/admin/rbac/roles")
def rbac_list(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    return rbac.list_roles()


@app.put("/admin/rbac/roles/{name}")
def rbac_put(name: str, payload: RolePayload, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    return rbac.upsert_role(name, payload.tools)


@app.delete("/admin/rbac/roles/{name}")
def rbac_del(name: str, request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    ok = rbac.delete_role(name)
    if not ok:
        raise HTTPException(status_code=404, detail="role not found")
    return {"deleted": True}


# ---------------------------------------------------------------------
# Admin: Auth status (Option B - external refresher)
# ---------------------------------------------------------------------
@app.get("/admin/auth/status")
def auth_status(request: Request, x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    _require_master(request, x_api_key, authorization)
    try:
        tok = token_list()
        total = len(tok)
        has_refresh = sum(1 for v in tok.values() if v.get("has_refresh"))
        return {"present": total > 0, "db_tokens": total, "with_refresh": has_refresh}
    except Exception as e:
        return {"present": False, "error": str(e)}


@app.get("/metrics")
def metrics():
    # No auth; deploy behind reverse proxy if needed
    txt = _render_metrics()
    return Response(content=txt, media_type="text/plain; version=0.0.4")

# ---------------------------------------------------------------------
# STDIO MCP 모드: stdin에서 JSON-RPC 요청을 읽고 stdout으로 응답을 출력
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    print("[MCP STDIO mode] Ready for JSON-RPC requests via stdin.", file=sys.stderr)
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": None, "error": {"code": -32700, "message": "Parse error"}}))
            continue
        if isinstance(payload, list):
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": None, "error": {"code": -32600, "message": "Batch not supported"}}))
            continue
        try:
            req = JsonRpcRequest.model_validate(payload)
        except ValidationError:
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": None, "error": {"code": -32600, "message": "Invalid Request"}}))
            continue
        if req.jsonrpc != MCP_JSONRPC_VERSION:
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32600, "message": "Invalid jsonrpc version"}}))
            continue
        method = req.method or ""
        params = req.params or {}
        if method == "initialize":
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": {
                "capabilities": CAPABILITIES["capabilities"],
                "server": CAPABILITIES["server"],
                "protocolRevision": MCP_PROTOCOL_REV
            }}))
            continue
        if method == "tools/list":
            tools, next_cursor = _list_tools(params.get("cursor"))
            result = {"tools": tools}
            if next_cursor is not None:
                result["nextCursor"] = next_cursor
            print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result}))
            continue
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not name or not isinstance(arguments, dict):
                print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32602, "message": "Invalid params"}}))
                continue
            try:
                result = _call_tool(name, arguments)
                print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result}))
            except TypeError as te:
                print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32602, "message": f"Invalid params: {str(te)}"}}))
            except Exception as e:
                logging.exception("server error on tools/call (STDIO)")
                print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32000, "message": f"Server error: {str(e)}"}}))
            continue
        print(json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32601, "message": "Method not found"}}))
