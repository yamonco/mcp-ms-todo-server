from __future__ import annotations
"""System defaults seeding (idempotent).

Seeds:
- Policy DB defaults are handled in app.auth.policy (_seed_defaults_if_empty).
- Groups: admins, powerusers, readers with reasonable defaults.

Reusability: leverage existing upsert_group() helper.
"""
from typing import List

from app.db import get_session
from app.models import Group
from app.apikeys import upsert_group


def _all_tool_names() -> List[str]:
    from app.tools import TOOLS_BY_NAME
    return sorted(TOOLS_BY_NAME.keys())


def _lite_tool_names() -> List[str]:
    # Prefer tag-based selection if available
    try:
        from app.tools import tools_by_tags
        names = tools_by_tags(["lite"])
        if names:
            return names
    except Exception:
        pass
    # Fallback minimal lite set
    return [
        "todo.lists.get",
        "todo.tasks.lite_list",
        "todo.tasks.lite_all",
        "todo.tasks.lite_complete",
        "todo.tasks.lite_snooze",
        "todo.sync.delta_lists",
        "todo.sync.delta_tasks",
        "todo.sync.walk_delta_lists",
        "todo.sync.walk_delta_tasks",
    ]


def _reader_tool_names() -> List[str]:
    base = {"todo.lists.get", "todo.tasks.get"}
    # include sync reads if present
    base |= {"todo.sync.delta_lists", "todo.sync.delta_tasks", "todo.sync.walk_delta_lists", "todo.sync.walk_delta_tasks"}
    from app.tools import TOOLS_BY_NAME
    return sorted([t for t in base if t in TOOLS_BY_NAME])


def seed_groups() -> None:
    """Ensure default groups exist (admins, powerusers, readers)."""
    with get_session() as s:
        existing = {g.name for g in s.query(Group).all()}
    # admins: all tools
    if "admins" not in existing:
        upsert_group("admins", _all_tool_names(), [])
    # powerusers: lite + write helpers if any
    if "powerusers" not in existing:
        tools = list(dict.fromkeys(_lite_tool_names()))  # preserve order unique
        upsert_group("powerusers", tools, ["lite"])  # tag retained for future expand
    # readers: read-only minimal
    if "readers" not in existing:
        upsert_group("readers", _reader_tool_names(), ["read"])  # tag marker only


def seed_defaults() -> None:
    try:
        seed_groups()
    except Exception:
        # best-effort; avoid blocking server start
        pass

