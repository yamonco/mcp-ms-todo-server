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

from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from app.tools import _list_tools, _call_tool
from app.config import cfg


 # Logging setup
logger = logging.getLogger("mcp")
logging.basicConfig(level=getattr(logging, cfg.log_level))


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
@app.get("/mcp/manifest")
def mcp_manifest():
    """
    MCP 툴 선언 manifest를 JSON으로 반환 (Cursor 등에서 자동 임포트 가능)
    """
    tools, _ = _list_tools(None)
    return {"tools": tools}

# SSE client registry (simple fan-out)
_sse_clients: set[asyncio.Queue[str]] = set()

@app.get("/mcp")
async def mcp_sse(request: Request):
    """Optional SSE stream for clients that open a separate event channel.
    We broadcast JSON-RPC responses as SSE data frames on this channel.
    """
    accept = request.headers.get("accept", "")
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
    allow_methods=["POST"],
    allow_headers=["*"],
    max_age=3600,
)

# API Key 인증 미들웨어
EXPECTED_API_KEY = cfg.api_key
def require_api_key(x_api_key: str = Header(None)):
    if EXPECTED_API_KEY:
        if not x_api_key or x_api_key != EXPECTED_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API Key")


@app.get("/health")
def health():
    # MCP 서버 상태, 버전, 인증 등 추가 정보 반환
    return {
        "status": "ok",
        "server": CAPABILITIES["server"],
        "protocolRevision": MCP_PROTOCOL_REV,
        "apiKeyRequired": bool(cfg.api_key),
        "tokenPresent": Path(cfg.token_file).exists(),
    }

@app.get("/mcp/capabilities")
def mcp_capabilities():
    # 서버 능력 공개(스펙: tools capability 선언)
    # TODO: MCP 최신 스펙 변화 시 server/capabilities notification 고려
    return CAPABILITIES



@app.post("/mcp")
async def mcp_entry(request: Request, x_api_key: str = Header(None)):
    # API Key 인증
    require_api_key(x_api_key)
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
        result = {"tools": tools}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        log_event("rpc", stage="tools/list")
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
            return _jsonrpc_err(req.id, -32602, "Invalid params", headers={"x-correlation-id": correlation_id})
        try:
            result = _call_tool(name, arguments)
            dt = int((time.time() - t0) * 1000)
            log_event("rpc", stage="tools/call", tool=name, ms=dt)
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
            return _jsonrpc_err(req.id, -32602, f"Invalid params: {str(te)}", headers={"x-correlation-id": correlation_id})
        except Exception as e:
            logger.exception("server error on tools/call")
            log_event("rpc.error", tool=name, reason="server_error", msg=str(e))
            return _jsonrpc_err(req.id, -32000, f"Server error: {str(e)}", headers={"x-correlation-id": correlation_id})

    log_event("rpc.error", reason="method_not_found")
    return _jsonrpc_err(req.id, -32601, "Method not found", headers={"x-correlation-id": correlation_id})

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
