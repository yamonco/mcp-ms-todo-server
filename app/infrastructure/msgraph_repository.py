from typing import Dict, Any, Optional
from app.domain.repositories import TodoRepository, TokenProvider
import app.adapter_graph_rest as rest


class MsGraphTodoRepository(TodoRepository):
    def __init__(self, token_provider: TokenProvider):
        self.token_provider = token_provider

    def _t(self) -> str:
        return self.token_provider.get_token()

    # Lists
    def list_lists(self) -> Dict[str, Any]:
        return rest.list_lists(self._t())

    def create_list(self, display_name: str) -> Dict[str, Any]:
        return rest.create_list(self._t(), display_name)

    def update_list(self, list_id: str, display_name: str) -> Dict[str, Any]:
        return rest.update_list(self._t(), list_id, display_name)

    def delete_list(self, list_id: str) -> Dict[str, Any]:
        return rest.delete_list(self._t(), list_id)

    # Tasks
    def list_tasks(self, list_id: str, *, filter_expr: Optional[str] = None, top: Optional[int] = None) -> Dict[str, Any]:
        return rest.list_tasks(self._t(), list_id, filter_expr=filter_expr, top=top)

    def create_task(
        self,
        list_id: str,
        title: str,
        *,
        body: Optional[str] = None,
        due: Optional[str] = None,
        time_zone: Optional[str] = None,
        reminder: Optional[str] = None,
        importance: Optional[str] = None,
        status: Optional[str] = None,
        recurrence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return rest.create_task(
            self._t(),
            list_id,
            title,
            body=body,
            due=due,
            time_zone=time_zone,
            reminder=reminder,
            importance=importance,
            status=status,
            recurrence=recurrence,
        )

    def update_task(self, list_id: str, task_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return rest.update_task(self._t(), list_id, task_id, patch)

    def delete_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return rest.delete_task(self._t(), list_id, task_id)

    # Convenience task ops
    def complete_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return rest.complete_task(self._t(), list_id, task_id)

    def reopen_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return rest.reopen_task(self._t(), list_id, task_id)

    def snooze_task(self, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> Dict[str, Any]:
        return rest.snooze_task(self._t(), list_id, task_id, remind_at_iso, tz)

    # Lite / Delta utilities
    def list_tasks_lite(self, list_id: str, top: int = 20) -> Dict[str, Any]:
        return rest.list_tasks_lite(self._t(), list_id, top)

    def list_tasks_all_lite(self, list_id: str, page_size: int = 100) -> Dict[str, Any]:
        return rest.list_tasks_all_lite(self._t(), list_id, page_size)

    def complete_task_lite(self, list_id: str, task_id: str) -> str:
        return rest.complete_task_lite(self._t(), list_id, task_id)

    def snooze_task_lite(self, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> str:
        return rest.snooze_task_lite(self._t(), list_id, task_id, remind_at_iso, tz)

    def delta_lists(self, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return rest.delta_lists(self._t(), delta_link)

    def delta_tasks(self, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return rest.delta_tasks(self._t(), list_id, delta_link)

    def walk_delta_lists(self, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return rest.walk_delta_lists(self._t(), delta_link)

    def walk_delta_tasks(self, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return rest.walk_delta_tasks(self._t(), list_id, delta_link)
