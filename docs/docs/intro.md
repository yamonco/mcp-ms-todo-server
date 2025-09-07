---
sidebar_position: 1
---

# Introduction

MCP‑MS‑TODO‑SERVER는 Microsoft Graph 기반의 To Do 통합 서버로, MCP(JSON‑RPC 2.0) 툴 인터페이스를 통해 작업을 자동화합니다. 모든 인증/토큰은 DB로만 관리하며, 앱 등록은 Microsoft Graph API로 일원화했습니다.

## Highlights
- JSON‑RPC 2.0 툴 서버 (`/mcp`)
- DB‑first 인증(토큰/앱 메타) — 파일 스토어 제거
- Graph API 기반 앱 등록(관리자 앱 권한), 디바이스 코드 제거
- Docker/uv 기반 개발/운영, Make 타겟 제공

빠른 시작은 [Getting Started](./getting-started.md)를 참고하세요.
