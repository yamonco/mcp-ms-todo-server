
 # main.py (2025 MCP latest structure)
 # - FastAPI-based MCP server
 # - All features are provided via a single JSON-RPC endpoint (/mcp) using tools/list, tools/call
 # - Service layer (TodoService) handles Graph API integration and business logic

import os
import json
import logging
from typing import Dict, Any, Callable, Optional, List, Tuple

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from service_todo import TodoService
from tools import ToolDef, TOOLS, TOOLS_BY_NAME, _list_tools, _call_tool, validate_params_by_schema


 # Logging setup
logger = logging.getLogger("mcp")
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))


 # MCP server meta/capabilities
MCP_JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_REV = "2025-06-18"  # Latest MCP revision

CAPABILITIES = {
    "capabilities": {
        "tools": {
            "listChanged": False
        }
    },
    "protocolRevision": MCP_PROTOCOL_REV,
    "server": {
        "name": "MCP ToDo Server",
        "version": "0.2.0"
    }
}

# === lists domain ===
def _exec_lists(p: Dict[str, Any], svc: TodoService):
    action = p.get("action")
    if action == "get":
        return svc.list_lists()
    if action == "create":
        return svc.create_list(display_name=p["display_name"])
    if action == "delete":
        return svc.delete_list(list_id=p["list_id"])
    if action == "rename":
        return svc.update_list(list_id=p["list_id"], display_name=p["display_name"])
    return {"error": f"unsupported lists.action: {action}"}

# === tasks domain ===
def _exec_tasks(p: Dict[str, Any], svc: TodoService):
    action = p.get("action")
    if action == "get":
    # Branch for lite (lightweight) or normal mode
        if p.get("lite") is True:
            top = p.get("top", 20)
            return svc.list_tasks_lite(list_id=p["list_id"], top=top)
        return svc.list_tasks(list_id=p["list_id"], user=p.get("user"))
    if action == "create":
        kw = {
            "body": p.get("body"),
            "due": p.get("due"),
            "time_zone": p.get("time_zone"),
            "reminder": p.get("reminder"),
            "importance": p.get("importance"),
            "status": p.get("status"),
            "recurrence": p.get("recurrence"),
        }
        kw = {k: v for k, v in kw.items() if v is not None}
        return svc.create_task(list_id=p["list_id"], title=p["title"], **kw)
    if action == "patch":
        mode = p.get("mode", "generic")
        if mode == "generic":
            return svc.update_task(list_id=p["list_id"], task_id=p["task_id"], patch=p["patch"])
        if mode == "complete":
            return svc.complete_task(list_id=p["list_id"], task_id=p["task_id"])
        if mode == "reopen":
            return svc.reopen_task(list_id=p["list_id"], task_id=p["task_id"])
        if mode == "snooze":
            return svc.snooze_task(list_id=p["list_id"], task_id=p["task_id"], remind_at_iso=p["remind_at_iso"], tz=p.get("tz", "Asia/Seoul"))
        return {"error": f"unsupported tasks.patch.mode: {mode}"}
    return {"error": f"unsupported tasks.action: {action}"}

# === sync/delta domain ===
def _exec_sync(p: Dict[str, Any], svc: TodoService):
    action = p.get("action")
    # lists / tasks / walk_lists / walk_tasks / lite_list / lite_all / lite_complete / lite_snooze
    if action == "delta_lists":
        return svc.delta_lists(delta_link=p.get("delta_link"))
    if action == "delta_tasks":
        return svc.delta_tasks(list_id=p["list_id"], delta_link=p.get("delta_link"))
    if action == "walk_delta_lists":
        return svc.walk_delta_lists(delta_link=p.get("delta_link"))
    if action == "walk_delta_tasks":
        return svc.walk_delta_tasks(list_id=p["list_id"], delta_link=p.get("delta_link"))
    if action == "lite_list":
        return svc.list_tasks_lite(list_id=p["list_id"], top=p.get("top", 20))
    if action == "lite_all":
        return svc.list_tasks_all_lite(list_id=p["list_id"], page_size=p.get("page_size", 100))
    if action == "lite_complete":
        return svc.complete_task_lite(list_id=p["list_id"], task_id=p["task_id"])
    if action == "lite_snooze":
        return svc.snooze_task_lite(list_id=p["list_id"], task_id=p["task_id"], remind_at_iso=p["remind_at_iso"], tz=p.get("tz", "Asia/Seoul"))
    return {"error": f"unsupported sync.action: {action}"}



# Index: name -> ToolDef
TOOLS_BY_NAME: Dict[str, ToolDef] = {t.name: t for t in TOOLS}

# ---------------------------------------------------------------------
# JSON-RPC 2.0 Model/Helper
# ---------------------------------------------------------------------
class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field(MCP_JSONRPC_VERSION)
    method: str
    id: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None

def _jsonrpc_ok(id_val: Any, result: Dict[str, Any]) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": id_val, "result": result})

def _jsonrpc_err(id_val: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse({"jsonrpc": MCP_JSONRPC_VERSION, "id": id_val, "error": {"code": code, "message": message}})

# tools/list result format
def _list_tools(cursor: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    # Return single page (implement cursor/nextCursor if needed)
    tool_defs = []
    for t in TOOLS:
        tool_defs.append({
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema
        })
    # According to MCP spec, nextCursor must be null even for a single page
    return tool_defs, None

# tools/call 실행 및 Tool Result 변환
def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Unknown tool → Unified as MCP ToolResult failure instead of JSON-RPC error
    if name not in TOOLS_BY_NAME:
        return {
            "content": [
                {"type": "text", "text": f"tool failed: unknown tool '{name}'"}
            ],
            "isError": True
        }

    tool = TOOLS_BY_NAME[name]

    # 간이 스키마 검증(강화판)
    err = validate_params_by_schema(arguments or {}, tool.inputSchema)
    if err:
        # 파라미터 유효성은 도구 호출 자체가 실패한 것으로 간주하지 않고,
        # JSON-RPC invalid params로 매핑(클라이언트 입력 오류)
        raise TypeError(err)

    try:
        # 민감 파라미터 노출 방지: 이름만 로그
        logger.debug("executing tool: %s", name)
        raw = tool.exec(arguments or {})
        return _wrap_tool_output(raw)
    except Exception as e:
        logger.exception("tool execution failed: %s", name)
        # 도구 내부 예외는 ToolResult 실패로 전달(상호운용성 안전)
        return {
            "content": [
                {"type": "text", "text": f"tool failed: {str(e)}"}
            ],
            "isError": True
        }

# ---------------------------------------------------------------------
# MCP 툴 결과 래퍼: content/isError 포맷 변환
# ---------------------------------------------------------------------
def _wrap_tool_output(raw):
    # dict, list, str 등 다양한 타입 지원
    if raw is None:
        return {"content": [{"type": "text", "text": "(no result)"}], "isError": False}
    if isinstance(raw, dict):
        # 에러 키 포함 시 isError
        if "error" in raw:
            return {"content": [{"type": "text", "text": str(raw["error"])}], "isError": True}
        return {"content": [{"type": "json", "json": raw}], "isError": False}
    if isinstance(raw, list):
        return {"content": [{"type": "json", "json": raw}], "isError": False}
    if isinstance(raw, str):
        return {"content": [{"type": "text", "text": raw}], "isError": False}
    # 기타 타입
    return {"content": [{"type": "text", "text": str(raw)}], "isError": False}

# ---------------------------------------------------------------------
# FastAPI 앱
# ---------------------------------------------------------------------


app = FastAPI(title="MCP ToDo Server", version="0.2.0")

# CORS 제한: 모든 Origin 차단 (필요시 특정 도메인만 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_methods=["POST"],
    allow_headers=["*"],
    max_age=3600
)

# API Key 인증 미들웨어
EXPECTED_API_KEY = os.getenv("API_KEY")
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
        "apiKeyRequired": bool(os.getenv("API_KEY")),
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
    is_sse = "text/event-stream" in accept

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

    # SSE 스트리밍 응답 핸들러
    async def sse_stream():
        import asyncio
        # 초기화/툴 목록은 한 번만 전송
        if method == "initialize":
            msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": {
                "capabilities": CAPABILITIES["capabilities"],
                "server": CAPABILITIES["server"],
                "protocolRevision": MCP_PROTOCOL_REV
            }})
            yield f"data: {msg}\n\n"
            return
        if method == "tools/list":
            cursor = params.get("cursor")
            tools, next_cursor = _list_tools(cursor)
            result = {"tools": tools}
            if next_cursor is not None:
                result["nextCursor"] = next_cursor
            msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "result": result})
            yield f"data: {msg}\n\n"
            return
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not name or not isinstance(arguments, dict):
                msg = json.dumps({"jsonrpc": MCP_JSONRPC_VERSION, "id": req.id, "error": {"code": -32602, "message": "Invalid params"}})
                yield f"data: {msg}\n\n"
                return
            try:
                # 진행 로그 예시: 툴 실행 시작
                yield f"data: {json.dumps({'event': 'start', 'tool': name})}\n\n"
                # 실제 툴 실행 (비동기 sleep으로 진행 로그 시뮬레이션)
                # 실서비스에서는 yield로 중간 로그/상태를 전송
                result = _call_tool(name, arguments)
                # 툴 실행 완료
                yield f"data: {json.dumps({'event': 'finish', 'tool': name})}\n\n"
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
        # 알 수 없는 메서드
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
        return _jsonrpc_ok(req.id, {
            "capabilities": CAPABILITIES["capabilities"],
            "server": CAPABILITIES["server"],
            "protocolRevision": MCP_PROTOCOL_REV
        })

    # -------------------------
    # tools/list
    # -------------------------
    if method == "tools/list":
        cursor = params.get("cursor")
        tools, next_cursor = _list_tools(cursor)
        result = {"tools": tools}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        return _jsonrpc_ok(req.id, result)

    # -------------------------
    # tools/call
    # -------------------------
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not name or not isinstance(arguments, dict):
            return _jsonrpc_err(req.id, -32602, "Invalid params")
        try:
            result = _call_tool(name, arguments)
            return _jsonrpc_ok(req.id, result)
        except TypeError as te:
            return _jsonrpc_err(req.id, -32602, f"Invalid params: {str(te)}")
        except Exception as e:
            logger.exception("server error on tools/call")
            return _jsonrpc_err(req.id, -32000, f"Server error: {str(e)}")

    return _jsonrpc_err(req.id, -32601, "Method not found")
