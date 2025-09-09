"""
Very small composition root (DI container) that wires repository/service
based on environment-driven config.
"""
from functools import lru_cache
from app.infrastructure.token_provider_authentik import AuthentikTokenProvider
from app.infrastructure.token_provider_db import DBTokenProvider
from app.infrastructure.msgraph_repository import MsGraphTodoRepository
from app.usecases.todo_service import TodoService
from app.config import cfg


@lru_cache(maxsize=128)
def get_todo_service_for(token_profile: str | None = None, *, token_id: int | None = None) -> TodoService:
    # Prefer DB token when token_profile/id is provided; fallback to Authentik
    if (token_id is not None) or (token_profile is not None and token_profile != ""):
        token = DBTokenProvider(token_profile=token_profile, token_id=token_id)
    else:
        token = AuthentikTokenProvider()
    repo = MsGraphTodoRepository(token)
    return TodoService(repo)
