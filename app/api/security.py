from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends, Header
from app.context import get_current_user_meta
from app.config import cfg
from app.integrations.authentik import introspect as ak_introspect, has_admin as ak_admin, meta_from_introspection as ak_meta
from app.context import set_current_user_meta
from app.db import get_session
from app.models import ApiKey, Token
try:
    from app.saas.license import verify_license as _verify_license  # type: ignore
except Exception:  # pragma: no cover
    def _verify_license(tenant_id: Optional[str], user_id: Optional[str]) -> bool:  # type: ignore
        return True


def _get_token_tenant_by_profile(profile: Optional[str]) -> Optional[str]:
    if not profile:
        return None
    try:
        with get_session() as s:
            t = s.query(Token).filter(Token.profile == profile).first()
            return t.tenant_id if t else None
    except Exception:
        return None


def get_provided_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    return (x_api_key or request.query_params.get("x-api-key") or None)


def _get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    lower = authorization.lower()
    if lower.startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def require_master(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # Accept Authentik admin bearer
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if ak_admin(info):
            set_current_user_meta({"master": True, **ak_meta(info or {}, bearer=btok)})
            return
    # Fallback to ADMIN_API_KEY for bootstrap/dev
    adm = cfg.api_key
    if adm and (x_api_key == adm or request.query_params.get("x-api-key") == adm):
        set_current_user_meta({"master": True, "name": "admin"})
        return
    if not cfg.authentik_enabled:
        # dev-open
        set_current_user_meta({"master": True, "name": "dev"})
        return
    raise HTTPException(status_code=403, detail="Admin token required")


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
    meta = get_current_user_meta() or {}
    tenant_id = _get_token_tenant_by_profile(meta.get("token_profile"))
    if not _verify_license(tenant_id, meta.get("user_id")):
        raise HTTPException(status_code=402, detail="License required")
    return None


def require_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # Allow Authentik bearer for general endpoints
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if info and info.get("active"):
            set_current_user_meta(ak_meta(info, bearer=btok))
            return
    # Fallback to X-API-Key for service-to-service or dev
    key = get_provided_key(request, x_api_key, authorization)
    if key:
        meta = _resolve_api_key_meta(key)
        if meta:
            set_current_user_meta(meta)
            return
    if not cfg.authentik_enabled:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="Invalid token or API key")


def require_user_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    # Require X-API-Key for MCP methods to track users/apps precisely
    key = get_provided_key(request, x_api_key, authorization)
    if key:
        meta = _resolve_api_key_meta(key)
        if meta:
            set_current_user_meta(meta)
            return
    # If none, allow Authentik bearer in dev or if explicitly configured
    if cfg.authentik_enabled:
        btok = _get_bearer_token(authorization)
        info = ak_introspect(btok)
        if info and info.get("active"):
            set_current_user_meta(ak_meta(info, bearer=btok))
            return
    if not cfg.authentik_enabled:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="X-API-Key required")


def _resolve_api_key_meta(key: str) -> Optional[Dict[str, Any]]:
    try:
        with get_session() as s:
            ak = s.query(ApiKey).filter(ApiKey.key == key, ApiKey.enabled == True).first()  # noqa: E712
            if not ak:
                return None
            meta: Dict[str, Any] = {
                "user_id": ak.user_id or ak.name or "",
                "name": ak.name or ak.user_id or "",
                "role": ak.role,
                "groups": list(ak.groups or []),
                "token_profile": ak.token_profile,
                "token_id": ak.token_id,
                "app_id": ak.app_id,
                "api_key": key,
            }
            return meta
    except Exception:
        return None
