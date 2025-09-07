---
sidebar_position: 1
---

# Overview

MCP‑MS‑TODO‑SERVER는 FastAPI 기반 MCP 서버로 Microsoft To Do(Graph API)를 통합합니다. 툴 호출은 `/mcp` JSON‑RPC로 통일되며, 인증/토큰은 DB에서만 관리합니다.

## Features
- JSON‑RPC 2.0 툴 서버, SSE 지원
- DB 토큰 스토어, RBAC(역할‑도구 매핑)
- Graph API 통합(앱 등록/재사용 자동화)
- Docker/uv 개발환경 + Make 워크플로

## Links
- [Getting Started](./getting-started.md)
- [API Reference](./api-reference.md)
- [Configuration](./configuration.md)
