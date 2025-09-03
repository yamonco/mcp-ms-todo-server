
 # service_todo.py (2025 MCP structure)
 # - TodoService: Handles Graph API integration and business logic
 # - Each method calls actual REST via adapter_graph_rest

import adapter_graph_rest as rest
import json
from pathlib import Path

def _get_access_token():
    """Return current access token (read from secrets/token.json or env TOKEN_PATH)"""
    import os
    config_path = Path(os.getenv("TOKEN_PATH", "/app/secrets/token.json"))
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config.get("access_token", "")
    return ""

class TodoService:
    """
    Actual business logic class called by MCP tool executor
    Each method calls Graph API, parameters are passed according to MCP tool spec
    """
    def update_list(self, list_id, display_name):
        token = _get_access_token()
        return rest.update_list(token, list_id, display_name)

    def list_lists(self):
        token = _get_access_token()
        return rest.list_lists(token)

    def create_list(self, display_name):
        token = _get_access_token()
        return rest.create_list(token, display_name)

    def list_tasks(self, list_id, user=None):
        token = _get_access_token()
    # The user parameter is currently unused. Can be used for $filter in the future.
        return rest.list_tasks(token, list_id)

    def create_task(self, list_id, title, body=None):
        token = _get_access_token()
        return rest.create_task(token, list_id, title, body)

    def update_task(self, list_id, task_id, patch):
        token = _get_access_token()
        return rest.update_task(token, list_id, task_id, patch)

    def delete_task(self, list_id, task_id):
        token = _get_access_token()
        return rest.delete_task(token, list_id, task_id)

    def delete_list(self, list_id):
        token = _get_access_token()
        return rest.delete_list(token, list_id)
