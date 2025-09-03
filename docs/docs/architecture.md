---
sidebar_position: 2
---

# Architecture

The project follows a clean, layered architecture:

- Domain: `app/domain` — repository and provider protocols
- Usecases: `app/usecases` — business services using repositories
- Infrastructure: `app/infrastructure` — token provider + Graph repository
- Interface: `app/tools` (tool schemas + executor), `app/main.py` (HTTP/SSE/STDIO)
- Composition Root: `app/container.py` — tiny DI wiring with caching

HTTP/Graph adapter (`app/adapter_graph_rest.py`) provides:
- Standardized request wrapper with rate limiting, circuit breaker and backoff
- Retry-After support for 429/5xx and pagination utilities
- Batch helpers (`$batch`) and selective field queries
- Convenience helpers for lite I/O and delta sync

This separation makes it easy to test, extend, and replace components.

