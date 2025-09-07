#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth helper entry point.
All implementation lives in modules (config, graph, dbsync, tokens, appreg, cli).
This file only dispatches to CLI to keep the package clean and maintainable.
"""
import os
import sys

# Ensure current directory is importable when executed as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli  # type: ignore

if __name__ == "__main__":
    raise SystemExit(cli.main())



def main():
    parser = argparse.ArgumentParser(description="AuthHelper CLI (no env)")
    parser.add_argument("--mcp-url", required=True, help="MCP 서버 URL (ex: http://localhost:8081)")
    parser.add_argument("--master-key", required=True, help="서버 관리자 API 키")
    parser.add_argument("--token-profile", default="default", help="토큰/메타 저장 프로필명")
    parser.add_argument("--tenant-id", default="organizations", help="Azure 테넌트 ID")
    parser.add_argument("--client-id", default="", help="앱 client_id (선택)")
    parser.add_argument("--scopes", default="Tasks.ReadWrite", help="OAuth2 scopes (공백구분)")
    # 나머지 명령/옵션은 기존 run_cmd에서 처리
    args, rest = parser.parse_known_args()
    helper = AuthHelper(
        mcp_url=args.mcp_url,
        master_key=args.master_key,
        token_profile=args.token_profile,
        tenant_id=args.tenant_id,
        client_id=args.client_id,
        scopes=args.scopes,
    )
    helper.run_cmd(rest)


if __name__ == "__main__":
    main()
