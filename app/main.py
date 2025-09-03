
 # main.py (2025 MCP latest structure)
 # - FastAPI-based MCP server
 # - All features are provided via a single JSON-RPC endpoint (/mcp) using tools/list, tools/call
 # - Service layer (TodoService) handles Graph API integration and business logic

import os
import json
import logging
from typing import Dict, Any, Callable, Optional, List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/mcp/capabilities")
def mcp_capabilities():
    # 서버 능력 공개(스펙: tools capability 선언)
    # TODO: MCP 최신 스펙 변화 시 server/capabilities notification 고려
    return CAPABILITIES


@app.post("/mcp")
async def mcp_entry(request: Request):
    """
    단일 JSON-RPC 엔드포인트
      - initialize
      - tools/list
      - tools/call
    """
    try:
        payload = await request.json()
    except Exception:
        return _jsonrpc_err(None, -32700, "Parse error")

    # 배치(JSON-RPC 배열) 미지원(일부 구현에서 배치 제거됨)
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
            # 파라미터 유효성(클라이언트 잘못) → JSON-RPC invalid params
            return _jsonrpc_err(req.id, -32602, f"Invalid params: {str(te)}")
        except Exception as e:
            logger.exception("server error on tools/call")
            # 서버 내부 예외 → JSON-RPC 서버 에러
            return _jsonrpc_err(req.id, -32000, f"Server error: {str(e)}")

    # 알 수 없는 메서드
    return _jsonrpc_err(req.id, -32601, "Method not found")
