# tools_manifest.py
# MCP 툴 선언 manifest를 .mcp.json 파일로 자동 생성

import os
import json
from app.tools import TOOLS, _list_tools

def main():
    tools, _ = _list_tools(None)
    manifest = {"tools": tools}
    with open(".mcp.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(".mcp.json manifest generated.")

if __name__ == "__main__":
    main()
