from __future__ import annotations
from .loader import load_helper_module

_mod = load_helper_module("graph")

# re-export public helpers
get_user_device_code_token = getattr(_mod, "get_user_device_code_token")
get_admin_access_token = getattr(_mod, "get_admin_access_token", None)
graph_request = getattr(_mod, "graph_request", None)

