from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends, Header
from app.context import get_current_user_meta
from app.config import cfg
from app.integrations.authentik import introspect as ak_introspect, has_admin as ak_admin, meta_from_introspection as ak_meta
from app.context import set_current_user_meta


def get_provided_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    # Legacy placeholder; we no longer accept API keys in authentik-only design.
    return None


def _get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    lower = authorization.lower()
    if lower.startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def require_master(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # Dev-open: allow if authentik disabled
    if not cfg.authentik_enabled:
        return
    # Accept authentik admin token
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if ak_admin(info):
            set_current_user_meta({"master": True, **ak_meta(info or {}, bearer=btok)})
            return
    raise HTTPException(status_code=403, detail="Master API key required")


# FastAPI dependency wrappers (declarative)
def dep_require_master(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None), request: Request = None):
    require_master(request, x_api_key, authorization)
    return None

def dep_require_api_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None), request: Request = None):
    require_api_key(request, x_api_key, authorization)
    return None

def dep_require_user_api_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None), request: Request = None):
    require_user_api_key(request, x_api_key, authorization)
    # Optional SaaS license enforcement (cloud mode)
    if (request is not None):
        meta = get_current_user_meta() or {}
        tenant_id = None
        tp = meta.get("token_profile")
        if tp:
            try:
                data = get_token_by_profile(tp)
                tenant_id = (data or {}).get("tenant_id")
            except Exception:
                tenant_id = None
        if not _verify_license(tenant_id, meta.get("user_id")):
            raise HTTPException(status_code=402, detail="License required")
    return None


def require_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # authentik bearer authentication (non-admin)
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if info and info.get("active"):
            set_current_user_meta(ak_meta(info, bearer=btok))
            return
    # Dev-open if authentik is disabled
    if not cfg.authentik_enabled:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def require_user_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # authentik bearer allowed for user endpoints
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if info and info.get("active"):
            set_current_user_meta(ak_meta(info, bearer=btok))
            return
    if not cfg.authentik_enabled:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="User bearer token required")
