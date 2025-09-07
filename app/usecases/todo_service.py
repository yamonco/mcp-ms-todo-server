from typing import Dict, Any, Optional
from app.domain.repositories import TodoRepository


class TodoService:
    def __init__(self, repo: TodoRepository):
        self.repo = repo

    # Lists
    def list_lists(self) -> Dict[str, Any]:
        return self.repo.list_lists()

    def create_list(self, display_name: str) -> Dict[str, Any]:
        return self.repo.create_list(display_name)

    def update_list(self, list_id: str, display_name: str) -> Dict[str, Any]:
        return self.repo.update_list(list_id, display_name)

    def delete_list(self, list_id: str) -> Dict[str, Any]:
        return self.repo.delete_list(list_id)

    def mutate_list(self, p: dict):
        action = (p or {}).get("action")
        if action == "create":
            return self.create_list(display_name=p["display_name"])  # type: ignore[index]
        if action == "delete":
            return self.delete_list(list_id=p["list_id"])  # type: ignore[index]
        if action == "rename":
            return self.update_list(list_id=p["list_id"], display_name=p["display_name"])  # type: ignore[index]
        return {"error": f"unsupported lists.action: {action}"}

    # Tasks
    def list_tasks(self, list_id: str, *, user: Optional[str] = None, top: Optional[int] = None, filter_expr: Optional[str] = None) -> Dict[str, Any]:
        # 'user' is reserved for future filtering
        return self.repo.list_tasks(list_id, filter_expr=filter_expr, top=top)

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
        return self.repo.create_task(
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
        return self.repo.update_task(list_id, task_id, patch)

    def delete_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return self.repo.delete_task(list_id, task_id)

    # Convenience (patch modes)
    def complete_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return self.repo.complete_task(list_id, task_id)

    def reopen_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return self.repo.reopen_task(list_id, task_id)

    def snooze_task(self, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> Dict[str, Any]:
        return self.repo.snooze_task(list_id, task_id, remind_at_iso, tz)

    # Lite / Delta
    def list_tasks_lite(self, list_id: str, top: int = 20) -> Dict[str, Any]:
        return self.repo.list_tasks_lite(list_id, top)

    def list_tasks_all_lite(self, list_id: str, page_size: int = 100) -> Dict[str, Any]:
        return self.repo.list_tasks_all_lite(list_id, page_size)

    def complete_task_lite(self, list_id: str, task_id: str) -> str:
        return self.repo.complete_task_lite(list_id, task_id)

    def snooze_task_lite(self, list_id: str, task_id: str, remind_at_iso: str, tz: str = "Asia/Seoul") -> str:
        return self.repo.snooze_task_lite(list_id, task_id, remind_at_iso, tz)

    def delta_lists(self, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return self.repo.delta_lists(delta_link)

    def delta_tasks(self, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return self.repo.delta_tasks(list_id, delta_link)

    def walk_delta_lists(self, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return self.repo.walk_delta_lists(delta_link)

    def walk_delta_tasks(self, list_id: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
        return self.repo.walk_delta_tasks(list_id, delta_link)
