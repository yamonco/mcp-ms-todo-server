from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends, Header
from app.config import cfg
from app.apikeys import list_keys as apikey_list, resolve_key
from app.context import set_current_user_meta


def get_provided_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if x_api_key:
        return x_api_key
    if authorization:
        lower = authorization.lower()
        if lower.startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        if lower.startswith("basic "):
            import base64
            try:
                raw = authorization.split(" ", 1)[1].strip()
                dec = base64.b64decode(raw).decode("utf-8", "ignore")
                if ":" in dec:
                    return dec.split(":", 1)[1]
            except Exception:
                pass
    try:
        ck = request.cookies.get("x-api-key") or request.cookies.get("api_key") or request.cookies.get("apikey")
        if ck:
            return ck
    except Exception:
        pass
    for qp in ("x-api-key", "api_key", "apikey"):
        val = request.query_params.get(qp)
        if val:
            return val
    return None


def require_master(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    provided = get_provided_key(request, x_api_key, authorization)
    # Dev-open: allow if no keys configured
    try:
        has_any_keys = bool(cfg.api_key) or bool(apikey_list())
    except Exception:
        has_any_keys = bool(cfg.api_key)
    if not has_any_keys:
        return
    if cfg.api_key and provided == cfg.api_key:
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
    return None


def require_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    provided = get_provided_key(request, x_api_key, authorization)
    if cfg.api_key and provided == cfg.api_key:
        set_current_user_meta({"master": True})
        return
    ok, meta = resolve_key(provided)
    if ok:
        set_current_user_meta(meta or None)
        return
    has_any_keys = bool(cfg.api_key) or bool(apikey_list())
    if not has_any_keys:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API Key")


def require_user_api_key(request: Request, x_api_key: Optional[str], authorization: Optional[str]) -> None:
    provided = get_provided_key(request, x_api_key, authorization)
    # Do not allow master here
    if cfg.api_key and provided == cfg.api_key:
        raise HTTPException(status_code=401, detail="User API key required (not master)")
    ok, meta = resolve_key(provided)
    if ok:
        set_current_user_meta(meta or None)
        return
    has_any_keys = bool(cfg.api_key) or bool(apikey_list())
    if not has_any_keys:
        set_current_user_meta(None)
        return
    raise HTTPException(status_code=401, detail="User API key required")
