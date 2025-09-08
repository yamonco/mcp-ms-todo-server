"""
Casbin policy integration (file or DB-backed) with helpers:
- filter_tools_for(meta, tools): for tools/list filtering
- enforce_tool(meta, tool_name): for tools/call execution guard

Subject priority: user_id -> name -> role -> "*"
Object: tool name
Action: "use"
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import time

_ENFORCER: Optional[object] = None
_MODEL_PATH: Optional[str] = None
_POLICY_PATH: Optional[str] = None
_MODEL_MTIME: float = 0.0
_POLICY_MTIME: float = 0.0


def _ensure_enforcer():
    global _ENFORCER
    if _ENFORCER is not None:
        return _ENFORCER
    model = os.getenv("CASBIN_MODEL")
    policy = os.getenv("CASBIN_POLICY")
    use_db = os.getenv("CASBIN_STORE", "").lower() in {"db", "database", "sqlalchemy"} or os.getenv("CASBIN_DB", "").lower() in {"1", "true", "yes"}
    if not model:
        _ENFORCER = False
        return _ENFORCER
    try:
        import casbin  # type: ignore
        if use_db:
            from app.auth.adapter_sqlalchemy import SqlAlchemyAdapter
            _seed_defaults_if_empty()
            adapter = SqlAlchemyAdapter()
            _set_paths(model, policy or "")
            _ENFORCER = casbin.Enforcer(model, adapter)
        else:
            if not policy:
                _ENFORCER = False
                return _ENFORCER
            _set_paths(model, policy)
            _ENFORCER = casbin.Enforcer(model, policy)
    except Exception:
        _ENFORCER = False
    return _ENFORCER


def _set_paths(model: str, policy: str) -> None:
    global _MODEL_PATH, _POLICY_PATH, _MODEL_MTIME, _POLICY_MTIME
    _MODEL_PATH, _POLICY_PATH = model, policy
    _MODEL_MTIME = _safe_mtime(model)
    _POLICY_MTIME = _safe_mtime(policy)


def _safe_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0


def reload() -> bool:
    enf = _ensure_enforcer()
    if not enf:
        return False
    try:
        import casbin  # type: ignore
        assert _MODEL_PATH is not None
        use_db = os.getenv("CASBIN_STORE", "").lower() in {"db", "database", "sqlalchemy"} or os.getenv("CASBIN_DB", "").lower() in {"1", "true", "yes"}
        if use_db:
            from app.auth.adapter_sqlalchemy import SqlAlchemyAdapter
            _seed_defaults_if_empty()
            adapter = SqlAlchemyAdapter()
            enforcer = casbin.Enforcer(_MODEL_PATH, adapter)
            globals()['_ENFORCER'] = enforcer
            _set_paths(_MODEL_PATH, _POLICY_PATH or "")
            return True
        else:
            assert _POLICY_PATH
            enforcer = casbin.Enforcer(_MODEL_PATH, _POLICY_PATH)
            globals()['_ENFORCER'] = enforcer
            _set_paths(_MODEL_PATH, _POLICY_PATH)
            return True
    except Exception:
        return False


def _hot_reload_if_changed() -> None:
    if not _ENFORCER or not _MODEL_PATH or not _POLICY_PATH:
        return
    m_mtime = _safe_mtime(_MODEL_PATH)
    p_mtime = _safe_mtime(_POLICY_PATH)
    if m_mtime != _MODEL_MTIME or p_mtime != _POLICY_MTIME:
        reload()


def filter_tools_for(meta: Dict[str, Any] | None, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enf = _ensure_enforcer()
    if not enf:
        return tools
    _hot_reload_if_changed()
    m = meta or {}
    subjects = []
    # consider user_id, name, role, and role:role
    for key in ("user_id", "name"):
        val = m.get(key)
        if val:
            subjects.append(val)
    role = m.get("role")
    if role:
        subjects.append(role)
        if ":" not in role:
            subjects.append(f"role:{role}")
    # include groups as subjects: group:<name>
    try:
        for g in (m.get("groups") or []):
            subjects.append(f"group:{g}")
    except Exception:
        pass
    subjects.append("*")
    out: List[Dict[str, Any]] = []
    for td in tools:
        obj = td.get("name") or ""
        allowed = False
        for sub in subjects:
            try:
                if enf.enforce(sub, obj, "use"):
                    allowed = True
                    break
            except Exception:
                continue
        if allowed:
            out.append(td)
    return out


def enforce_tool(meta: Dict[str, Any] | None, tool_name: str) -> bool:
    enf = _ensure_enforcer()
    if not enf:
        return True
    _hot_reload_if_changed()
    m = meta or {}
    subjects = []
    for key in ("user_id", "name"):
        val = m.get(key)
        if val:
            subjects.append(val)
    role = m.get("role")
    if role:
        subjects.append(role)
        if ":" not in role:
            subjects.append(f"role:{role}")
    try:
        for g in (m.get("groups") or []):
            subjects.append(f"group:{g}")
    except Exception:
        pass
    subjects.append("*")
    for sub in subjects:
        try:
            if enf.enforce(sub, tool_name or "", "use"):
                return True
        except Exception:
            continue
    return False


def _seed_defaults_if_empty() -> None:
    """Seed default Casbin policies if DB is enabled and empty.
    - Allow role:all to use all tools
    - Lite role: allow a safe subset matching previous defaults
    Runs once when casbin_rule is empty.
    """
    try:
        from app.db import get_session
        from app.models import CasbinRule
        with get_session() as s:
            cnt = s.query(CasbinRule).count()
            if cnt and cnt > 0:
                return
            # role:all → all tools
            s.add(CasbinRule(ptype="p", v0="role:all", v1="*", v2="use"))
            # role:lite → limited tools
            lite_tools = [
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
            for t in lite_tools:
                s.add(CasbinRule(ptype="p", v0="role:lite", v1=t, v2="use"))
    except Exception:
        # best-effort; ignore seed errors
        pass
