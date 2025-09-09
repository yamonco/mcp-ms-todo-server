---
sidebar_position: 2
---

# Architecture (Clean + DB Tokens)

Layers:
- Domain (`app/domain`): repository/provider protocols
- Usecases (`app/usecases`): `TodoService` and business logic
- Infrastructure (`app/infrastructure`): `MsGraphTodoRepository`, `DBTokenProvider`
- Interface: `app/tools` (schemas + exec), `app/main.py` (HTTP/SSE/STDIO JSON-RPC)
- Composition Root: `app/container.py` (DI wiring with caching)

Graph Adapter (`app/adapter_graph_rest.py`):
- Rate limiting, circuit breaker, backoff, pagination, `$batch`
- Lite endpoints and delta sync helpers

Auth Helper (modular, in `app/auth_helper/`):
- `config.py` (env → Settings), `graph.py` (Graph admin token), `dbsync.py` (Admin API upsert/verify)
- `tokens.py` (validate/refresh/load/save), `appreg.py` (register/reuse app), `cli.py` (commands)
- All tokens/meta live in DB; no JSON token files.
