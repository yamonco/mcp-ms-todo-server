"""
Simple smoke tests for MCP server in-process.
Usage:
  API_KEY=test-key TOOL_SCHEMA_DIR=./app/tools python smoke_test.py
"""
import os
import os.path

# ensure defaults for local run (DB-only)
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("TOOL_SCHEMA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "app", "tools")))
os.environ.setdefault("DB_URL", "sqlite:///./secrets/test.db")
os.environ.setdefault("DB_AUTO_CREATE", "true")

from fastapi.testclient import TestClient

# Create schema explicitly for tests
from app.models import Base
from app.db import ensure_schema
ensure_schema(Base)

from app.main import app

client = TestClient(app)


def must(cond: bool, msg: str = "assertion failed"):
    if not cond:
        raise SystemExit(f"SMOKE FAIL: {msg}")


def main():
    # 1) health without key should 401
    r = client.get("/health")
    must(r.status_code == 401, f"/health expected 401, got {r.status_code}")

    # 2) health with key
    r = client.get("/health", headers={"x-api-key": os.environ["API_KEY"]})
    must(r.status_code == 200, f"/health expected 200, got {r.status_code}")
    j = r.json()
    must(j.get("status") == "ok", "health status not ok")

    # 3) manifest with key
    r = client.get("/mcp/manifest", headers={"x-api-key": os.environ["API_KEY"]})
    must(r.status_code == 200, f"/mcp/manifest expected 200, got {r.status_code}")
    j = r.json()
    must(isinstance(j.get("tools"), list), "manifest tools missing")

    # 4) JSON-RPC initialize
    payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    r = client.post("/mcp", headers={"x-api-key": os.environ["API_KEY"]}, json=payload)
    must(r.status_code == 200, f"/mcp initialize expected 200, got {r.status_code}")
    j = r.json()
    must(j.get("result", {}).get("server", {}).get("name"), "initialize missing server name")

    # 5) tools/list
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    r = client.post("/mcp", headers={"x-api-key": os.environ["API_KEY"]}, json=payload)
    must(r.status_code == 200, "/mcp tools/list expected 200")
    j = r.json().get("result", {})
    must(isinstance(j.get("tools"), list), "tools/list returned no tools")

    # 6) tools/call invalid params → -32602
    payload = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "todo.tasks.create", "arguments": {}}}
    r = client.post("/mcp", headers={"x-api-key": os.environ["API_KEY"]}, json=payload)
    must(r.status_code == 200, "/mcp tools/call expected 200")
    j = r.json()
    must(j.get("error", {}).get("code") == -32602, "tools/call invalid param code mismatch")

    print("SMOKE OK")


if __name__ == "__main__":
    main()
