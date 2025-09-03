"""
Very small composition root (DI container) that wires repository/service
based on environment-driven config.
"""
from functools import lru_cache
from app.infrastructure.token_provider import FileTokenProvider
from app.infrastructure.msgraph_repository import MsGraphTodoRepository
from app.usecases.todo_service import TodoService


@lru_cache(maxsize=1)
def get_todo_service() -> TodoService:
    token = FileTokenProvider()
    repo = MsGraphTodoRepository(token)
    return TodoService(repo)

