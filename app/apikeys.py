import secrets
from typing import Dict, Any, Optional, Tuple

from app.config import cfg
from app.db import get_engine, get_session
from app.models import ApiKey, Token, App, ApiKeyTool, Group, GroupTool, ApiKeyGroup


def list_keys() -> Dict[str, Any]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    out: Dict[str, Any] = {}
    with get_session() as s:
        keys = s.query(ApiKey).all()
        tools_map: Dict[str, list[str]] = {}
        for row in s.query(ApiKeyTool).all():
            tools_map.setdefault(row.key, []).append(row.tool)
        group_map: Dict[str, list[str]] = {}
        for row in s.query(ApiKeyGroup).all():
            group_map.setdefault(row.key, []).append(row.group)
        group_tools: Dict[str, list[str]] = {}
        for row in s.query(GroupTool).all():
            group_tools.setdefault(row.group, []).append(row.tool)
        for rec in keys:
            # compute effective allowed tools = direct tools ∪ union(group tools)
            groups = group_map.get(rec.key, [])
            gtools = set()
            for g in groups:
                for t in group_tools.get(g, []):
                    gtools.add(t)
            effective = sorted(set(tools_map.get(rec.key, [])) | gtools)
            out[rec.key] = {
                "template": rec.template or "",
                "allowed_tools": effective,
                "note": rec.note or "",
                "user_id": rec.user_id or "",
                "name": rec.name or "",
                "token_profile": rec.token_profile or "",
                "token_id": rec.token_id,
                "role": rec.role or "",
                "app_id": rec.app_id,
                "groups": groups,
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
    app_id: Optional[int] = None,
    app_profile: Optional[str] = None,
    groups: Optional[list[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    template = (template or "").lower()
    # 템플릿 간소화: lite/all/custom만 지원
    allowed_templates = {"lite", "all", "custom"}
    if template not in allowed_templates:
        raise ValueError(f"template must be one of: {', '.join(sorted(allowed_templates))}")
    # template ↔ role 매핑: custom은 None, 나머지는 template명 그대로
    if role is None:
        role = None if template == "custom" else template

    allowed = []
    if template == "custom":
        if not allowed_tools:
            raise ValueError("allowed_tools required for custom template")
        allowed = allowed_tools
    else:
        allowed = _lite_tool_names() if template == "lite" else _all_tool_names()

    resolved_app_id: Optional[int] = app_id
    if resolved_app_id is None and app_profile:
        with get_session() as s:
            app = s.query(App).filter(App.profile == app_profile).first()
            if app:
                resolved_app_id = app.id
    # 템플릿에 의한 app 제한 제거(간소화)
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
        "app_id": resolved_app_id,
        "groups": sorted(set(groups or [])),
    }
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for api-keys store")
    with get_session() as s:
        s.add(ApiKey(
            key=key,
            template=meta.get("template"),
            note=meta.get("note"),
            user_id=meta.get("user_id"),
            name=meta.get("name"),
            token_profile=meta.get("token_profile"),
            token_id=meta.get("token_id"),
            role=meta.get("role"),
            app_id=meta.get("app_id"),
        ))
        for t in meta.get("allowed_tools", []):
            s.add(ApiKeyTool(key=key, tool=t))
        for g in meta.get("groups", []):
            s.add(ApiKeyGroup(key=key, group=g))
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
        # key direct tools
        tools = [r.tool for r in s.query(ApiKeyTool).filter(ApiKeyTool.key == key).all()]
        # key groups and tools from those groups
        groups = [r.group for r in s.query(ApiKeyGroup).filter(ApiKeyGroup.key == key).all()]
        group_tools = []
        group_tags = []
        if groups:
            gtools = s.query(GroupTool).filter(GroupTool.group.in_(groups)).all()
            group_tools = [x.tool for x in gtools]
            from app.models import GroupTag
            gtags = s.query(GroupTag).filter(GroupTag.group.in_(groups)).all()
            group_tags = [x.tag for x in gtags]
        tag_tools = _tools_by_tags(group_tags) if group_tags else []
        effective = sorted(set(tools) | set(group_tools) | set(tag_tools))
        meta = {
            "template": rec.template or "",
            "allowed_tools": effective,
            "note": rec.note or "",
            "user_id": rec.user_id or "",
            "name": rec.name or "",
            "token_profile": rec.token_profile or "",
            "token_id": rec.token_id,
            "role": rec.role or "",
            "app_id": rec.app_id,
            "groups": groups,
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
            "app_id",
            "groups",
        }
        for k, v in list(updates.items()):
            if k not in allowed_fields or v is None:
                continue
            if k == "allowed_tools":
                s.query(ApiKeyTool).filter(ApiKeyTool.key == key).delete()
                for t in v:
                    s.add(ApiKeyTool(key=key, tool=t))
                continue
            if k == "groups":
                s.query(ApiKeyGroup).filter(ApiKeyGroup.key == key).delete()
                for g in v:
                    s.add(ApiKeyGroup(key=key, group=g))
                continue
            setattr(rec, k, v)
        tools = [r.tool for r in s.query(ApiKeyTool).filter(ApiKeyTool.key == key).all()]
        groups = [r.group for r in s.query(ApiKeyGroup).filter(ApiKeyGroup.key == key).all()]
        gtools = [x.tool for x in s.query(GroupTool).filter(GroupTool.group.in_(groups)).all()] if groups else []
        from app.models import GroupTag
        gtags = [x.tag for x in s.query(GroupTag).filter(GroupTag.group.in_(groups)).all()] if groups else []
        ttools = _tools_by_tags(gtags) if gtags else []
        effective = sorted(set(tools) | set(gtools) | set(ttools))
        return {
            "template": rec.template or "",
            "allowed_tools": effective,
            "note": rec.note or "",
            "user_id": rec.user_id or "",
            "name": rec.name or "",
            "token_profile": rec.token_profile or "",
            "token_id": rec.token_id,
            "role": rec.role or "",
            "app_id": rec.app_id,
            "groups": groups,
        }

# Group policy admin helpers
def _tools_by_tags(tags: list[str]) -> list[str]:
    # late import to avoid cyc deps
    from app.tools import TOOLS
    out: set[str] = set()
    tgset = set(tags or [])
    for t in TOOLS:
        tt = set((t.get("tags") or []))
        if tgset & tt:
            out.add(t.get("name"))
    return sorted(out)


def list_groups() -> Dict[str, Any]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for groups store")
    out: Dict[str, Any] = {}
    with get_session() as s:
        for g in s.query(Group).all():
            tools = [r.tool for r in s.query(GroupTool).filter(GroupTool.group == g.name).all()]
            # tags are represented as special pseudo-tools prefixed? Better: store in separate table, but keep simple
            # For explicit tags storage, we reuse GroupTool with 'tag:' prefix? We added GroupTag model instead.
            from app.models import GroupTag
            tags = [r.tag for r in s.query(GroupTag).filter(GroupTag.group == g.name).all()]
            out[g.name] = {"tools": tools, "tags": tags}
    return out

def upsert_group(name: str, tools: list[str], tags: list[str] | None = None) -> Dict[str, Any]:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for groups store")
    with get_session() as s:
        grp = s.get(Group, name)
        if not grp:
            grp = Group(name=name)
            s.add(grp)
        s.query(GroupTool).filter(GroupTool.group == name).delete()
        for t in tools:
            s.add(GroupTool(group=name, tool=t))
        from app.models import GroupTag
        s.query(GroupTag).filter(GroupTag.group == name).delete()
        for tag in (tags or []):
            s.add(GroupTag(group=name, tag=tag))
    return list_groups()

def delete_group(name: str) -> bool:
    if not get_engine():
        raise RuntimeError("DB_URL must be configured for groups store")
    with get_session() as s:
        grp = s.get(Group, name)
        if not grp:
            return False
        s.query(GroupTool).filter(GroupTool.group == name).delete()
        from app.models import GroupTag
        s.query(GroupTag).filter(GroupTag.group == name).delete()
        s.query(ApiKeyGroup).filter(ApiKeyGroup.group == name).delete()
        s.delete(grp)
        return True
