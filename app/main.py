import os, json, asyncio, logging
from typing import Dict, Any

from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from dotenv import load_dotenv
load_dotenv()

from .tools_todo import TOOLS

app = FastAPI(title="MCP ToDo Server", version="0.1.0")
logger = logging.getLogger("mcp")
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL","INFO")))

@app.get("/health")
async def health():
    return {"status":"ok"}

async def _stream_tool(tool: str, params: Dict[str, Any]):
    # Streaming generator for SSE
    if tool not in TOOLS:
        yield {"event":"error", "data": {"error":"unknown_tool"}}
        return
    yield {"event":"progress", "data":{"step":"start", "tool":tool}}
    try:
        fn = TOOLS[tool]
        result = fn(params or {})
        yield {"event":"result", "data":{"tool":tool, "ok":True, "result":result}}
    except Exception as e:
        yield {"event":"error", "data":{"tool":tool, "ok":False, "error": str(e)}}
    finally:
        yield {"event":"done", "data":{"tool":tool}}

@app.post("/mcp/tools/call")
async def mcp_tools_call(request: Request):
    # Content-Type: application/json
    payload = await request.json()
    tool = payload.get("tool")
    params = payload.get("params", {})
    accept = request.headers.get("accept","")
    if "text/event-stream" in accept:
        async def event_gen():
            async for ev in _asyncify(_stream_tool(tool, params)):
                yield {"event": ev["event"], "data": json.dumps(ev["data"], ensure_ascii=False)}
        return EventSourceResponse(event_gen())
    # non-streaming fallback
    if tool not in TOOLS:
        raise HTTPException(404, "unknown_tool")
    try:
        res = TOOLS[tool](params)
        return {"ok": True, "result": res}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

async def _asyncify(gen):
    # wrap sync generator to async generator
    loop = asyncio.get_event_loop()
    for item in gen:
        yield item
        await asyncio.sleep(0)
