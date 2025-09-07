import secrets
from typing import Dict, Any, Optional, Tuple

from app.config import cfg
from app.db import get_engine, get_session
from app.models import ApiKey, Token


def list_keys() -> Dict[str, Any]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    out: Dict[str, Any] = {}
    with get_session() as s:
        for rec in s.query(ApiKey).all():
            out[rec.key] = {
                "template": rec.template or "",
                "allowed_tools": (rec.allowed_tools or {}).get("items", []) if isinstance(rec.allowed_tools, dict) else [],
                "note": rec.note or "",
                "user_id": rec.user_id or "",
                "name": rec.name or "",
                "token_profile": rec.token_profile or "",
                "token_id": rec.token_id,
                "role": rec.role or "",
            }
    return out


def delete_key(key: str) -> bool:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    with get_session() as s:
        rec = s.get(ApiKey, key)
        if not rec:
            return False
        s.delete(rec)
        return True


def _all_tool_names() -> list[str]:
    # late import to avoid cyc deps
    from app.tools import TOOLS_BY_NAME
    return list(TOOLS_BY_NAME.keys())


def _lite_tool_names() -> list[str]:
    # conservative lite set
    base = {
        "todo.lists.get",
        "todo.tasks.lite_list",
        "todo.tasks.lite_all",
        "todo.tasks.lite_complete",
        "todo.tasks.lite_snooze",
    }
    # include read-only sync helpers if present
    for t in ("todo.sync.delta_lists", "todo.sync.delta_tasks", "todo.sync.walk_delta_lists", "todo.sync.walk_delta_tasks"):
        base.add(t)
    from app.tools import TOOLS_BY_NAME
    return [t for t in base if t in TOOLS_BY_NAME]


def generate_api_key(
    template: str,
    *,
    allowed_tools: Optional[list[str]] = None,
    note: Optional[str] = None,
    user_id: Optional[str] = None,
    name: Optional[str] = None,
    token_profile: Optional[str] = None,
    token_id: Optional[int] = None,
    role: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    template = (template or "").lower()
    if template not in {"lite", "default", "custom"}:
        raise ValueError("template must be one of: lite, default, custom")
    # template ↔ role 매핑(간소화): lite→lite, default→default, custom→None
    if role is None:
        role = template if template in ("lite", "default") else None

    if template == "custom":
        if not allowed_tools:
            raise ValueError("allowed_tools required for custom template")
        allowed = allowed_tools
    elif template == "lite":
        # 경량 기본 셋(역호환). RBAC 역할이 있으면 서버에서 역할 기반으로 해석하므로 여기 리스트는 참고값
        allowed = _lite_tool_names()
    else:
        allowed = _all_tool_names()

    key = secrets.token_urlsafe(24)
    meta = {
        "template": template,
        "allowed_tools": sorted(set(allowed)),
        "note": note or "",
        "user_id": user_id or "",
        "name": name or "",
        "token_profile": token_profile or "",
        "token_id": token_id,
        "role": role or "",
    }
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    with get_session() as s:
        s.add(ApiKey(
            key=key,
            template=meta.get("template"),
            allowed_tools={"items": meta.get("allowed_tools", [])},
            note=meta.get("note"),
            user_id=meta.get("user_id"),
            name=meta.get("name"),
            token_profile=meta.get("token_profile"),
            token_id=meta.get("token_id"),
            role=meta.get("role"),
        ))
    return key, meta


def resolve_key(key: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if not key:
        return False, None
    if not get_engine():
        return False, None
    with get_session() as s:
        rec = s.get(ApiKey, key)
        if not rec:
            return False, None
        meta = {
            "template": rec.template or "",
            "allowed_tools": (rec.allowed_tools or {}).get("items", []) if isinstance(rec.allowed_tools, dict) else [],
            "note": rec.note or "",
            "user_id": rec.user_id or "",
            "name": rec.name or "",
            "token_profile": rec.token_profile or "",
            "token_id": rec.token_id,
            "role": rec.role or "",
        }
        return True, meta


def list_users() -> Dict[str, Any]:
    return list_keys()


def update_key(key: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    with get_session() as s:
        rec = s.get(ApiKey, key)
        if not rec:
            return None
        allowed_fields = {
            "template",
            "allowed_tools",
            "note",
            "user_id",
            "name",
            "token_profile",
            "token_id",
            "role",
        }
        for k, v in list(updates.items()):
            if k not in allowed_fields or v is None:
                continue
            if k == "allowed_tools":
                rec.allowed_tools = {"items": v}
            else:
                setattr(rec, k, v)
        return {
            "template": rec.template or "",
            "allowed_tools": (rec.allowed_tools or {}).get("items", []) if isinstance(rec.allowed_tools, dict) else [],
            "note": rec.note or "",
            "user_id": rec.user_id or "",
            "name": rec.name or "",
            "token_profile": rec.token_profile or "",
            "token_id": rec.token_id,
            "role": rec.role or "",
        }
