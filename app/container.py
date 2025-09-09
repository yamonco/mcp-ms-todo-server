"""
Very small composition root (DI container) that wires repository/service
based on environment-driven config.
"""
from functools import lru_cache
from app.infrastructure.token_provider_authentik import AuthentikTokenProvider
from app.infrastructure.msgraph_repository import MsGraphTodoRepository
from app.usecases.todo_service import TodoService
from app.config import cfg


@lru_cache(maxsize=128)
def get_todo_service_for(token_profile: str | None = None, *, token_id: int | None = None) -> TodoService:
    # Authentik-only design
    token = AuthentikTokenProvider()
    repo = MsGraphTodoRepository(token)
    return TodoService(repo)
