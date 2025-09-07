import json
from typing import Dict, List, Optional

from app.db import get_engine, get_session
from app.models import Role


def _load_roles() -> Dict[str, List[str]]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for RBAC roles store")
    out: Dict[str, List[str]] = {}
    with get_session() as s:
        for r in s.query(Role).all():
            tools = list((r.tools or {}).get("items", [])) if isinstance(r.tools, dict) else []
            out[r.name] = tools
    return out


def _save_roles(roles: Dict[str, List[str]]):
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for RBAC roles store")
    with get_session() as s:
        existing = {r.name: r for r in s.query(Role).all()}
        for name, tools in roles.items():
            rec = existing.pop(name, None)
            payload = {"items": tools}
            if rec:
                rec.tools = payload
            else:
                s.add(Role(name=name, tools=payload))
        for rec in existing.values():
            s.delete(rec)


def list_roles() -> Dict[str, List[str]]:
    return _load_roles()


def get_role(name: str) -> Optional[List[str]]:
    return _load_roles().get(name)


def upsert_role(name: str, tools: List[str]) -> Dict[str, List[str]]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for RBAC roles store")
    with get_session() as s:
        rec = s.get(Role, name)
        payload = {"items": tools}
        if rec:
            rec.tools = payload
        else:
            s.add(Role(name=name, tools=payload))
    return _load_roles()


def delete_role(name: str) -> bool:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for RBAC roles store")
    with get_session() as s:
        rec = s.get(Role, name)
        if not rec:
            return False
        s.delete(rec)
        return True


def resolve_allowed_tools_for_role(role: str) -> Optional[List[str]]:
    if not role:
        return None
    if role == "default":
        # default = 모든 툴 허용 → None 반환하여 필터 미적용 신호
        return None
    roles = _load_roles()
    return roles.get(role)
