---
sidebar_position: 2
---

# 아키텍처 (Clean + DB Tokens)

레이어
- Domain, Usecases, Infrastructure(DBTokenProvider, MsGraphTodoRepository)
- Interface(`/mcp` JSON‑RPC), Composition Root(app/container.py)

Graph 어댑터(app/adapter_graph_rest.py)
- 레이트리밋/사이킷브레이커/백오프/페이지네이션/배치

Auth Helper(`app/auth_helper/`)
- config/graph/dbsync/tokens/appreg/cli 로 분리
- 모든 토큰/메타는 DB에만 저장
