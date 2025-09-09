from __future__ import annotations
"""
System defaults seeding (idempotent).

Seeds:
- Policy DB defaults are handled in app.auth.policy (_seed_defaults_if_empty).
- Groups: admins, powerusers, readers with reasonable defaults.

Reusability: leverage existing upsert_group() helper.
"""

import json
from pathlib import Path
from typing import List

from app.config import cfg


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
    return None


def seed_templates() -> None:
    return None


def seed_defaults() -> None:
    try:
        seed_groups()
    except Exception:
        pass
    try:
        seed_templates()
    except Exception:
        pass


def seed_env_credentials() -> None:
    return None
