from __future__ import annotations
from typing import Optional, Dict, Any, List
import base64
import httpx
from app.config import cfg


def _basic_auth_header(client_id: Optional[str], client_secret: Optional[str]) -> Optional[str]:
    if not client_id or client_secret is None:
        return None
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def introspect(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    if not (cfg.authentik_enabled and cfg.authentik_introspection_url):
        return None
    try:
        headers = {"content-type": "application/x-www-form-urlencoded"}
        ba = _basic_auth_header(cfg.authentik_client_id, cfg.authentik_client_secret)
        if ba:
            headers["authorization"] = ba
        data = {"token": token}
        with httpx.Client(timeout=5.0) as c:
            r = c.post(cfg.authentik_introspection_url, data=data, headers=headers)
            if r.status_code != 200:
                return None
            js = r.json()
            return js if isinstance(js, dict) else None
    except Exception:
        return None


def _roles_from_info(info: Dict[str, Any]) -> List[str]:
    # authentik commonly exposes scopes in 'scope' string; roles may be mapped to scopes or custom claims
    roles: List[str] = []
    try:
        roles += list((info.get("scope") or "").split())
    except Exception:
        pass
    # optionally support realm/client role arrays if present (compatible shape)
    try:
        roles += list((info.get("realm_access") or {}).get("roles") or [])
    except Exception:
        pass
    try:
        for _, v in (info.get("resource_access") or {}).items():
            roles += list((v or {}).get("roles") or [])
    except Exception:
        pass
    return roles


def has_admin(info: Optional[Dict[str, Any]]) -> bool:
    if not info or not info.get("active"):
        return False
    roles = _roles_from_info(info)
    return cfg.authentik_admin_role in roles


def meta_from_introspection(info: Dict[str, Any], *, bearer: Optional[str] = None) -> Dict[str, Any]:
    sub = info.get("sub") or info.get("username") or info.get("preferred_username") or ""
    roles = _roles_from_info(info)
    role = None
    for r in roles:
        if r.startswith(cfg.authentik_role_prefix):
            role = r[len(cfg.authentik_role_prefix):]
            break
    groups = []
    gclaim = cfg.authentik_groups_claim
    try:
        val = info.get(gclaim)
        if isinstance(val, list):
            groups = [str(x) for x in val]
    except Exception:
        pass
    meta: Dict[str, Any] = {
        "user_id": sub,
        "name": info.get("preferred_username") or sub,
        "role": role,
        "groups": groups,
        "authentik": {k: info.get(k) for k in ("client_id", "exp", "nbf", "aud", "iss") if k in info},
    }
    if bearer:
        meta["authentik_access_token"] = bearer
    ga = info.get(cfg.authentik_graph_access_claim)
    gr = info.get(cfg.authentik_graph_refresh_claim)
    if ga or gr:
        meta["graph"] = {"access_token": ga, "refresh_token": gr}
    return meta

