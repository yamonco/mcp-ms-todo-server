from __future__ import annotations
import secrets
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.security import dep_require_master
from app.db import get_session
from app.models import App, Token, ApiKey
from app.context import get_current_user_meta
import json, base64


router = APIRouter()


class AppUpsert(BaseModel):
    profile: Optional[str] = None
    display_name: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None
    subscription_id: Optional[str] = None


@router.get("/admin/apps")
def list_apps(_: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        rows = s.query(App).order_by(App.updated_at.desc()).all()
        return {"items": [
            {
                "id": x.id,
                "profile": x.profile,
                "display_name": x.display_name,
                "tenant_id": x.tenant_id,
                "client_id": x.client_id,
                "scopes": x.scopes,
                "subscription_id": x.subscription_id,
                "updated_at": x.updated_at.isoformat(),
            } for x in rows
        ]}


@router.post("/admin/apps")
def upsert_app(data: AppUpsert, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        row = None
        if data.profile:
            row = s.query(App).filter(App.profile == data.profile).first()
        if not row:
            row = App()
        for f in ("profile", "display_name", "tenant_id", "client_id", "scopes", "subscription_id"):
            setattr(row, f, getattr(data, f))
        s.add(row)
        s.flush()
        return {"id": row.id, "profile": row.profile}


class RegisterOrReuse(BaseModel):
    app_prefix: str
    display_name: Optional[str] = None


@router.post("/admin/apps/register_or_reuse")
def register_or_reuse(data: RegisterOrReuse, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    # No external registration here; reuse by prefix, else create a new stub entry
    prefix = data.app_prefix
    with get_session() as s:
        existing = s.query(App).filter(App.profile.like(f"{prefix}%")).order_by(App.updated_at.desc()).first()
        if existing:
            return {"reused": True, "app": {"id": existing.id, "profile": existing.profile}}
        # create stub profile
        prof = f"{prefix}-{int(time.time())}"
        row = App(profile=prof, display_name=data.display_name or prof)
        s.add(row)
        s.flush()
        return {"reused": False, "app": {"id": row.id, "profile": row.profile}}


class TokenUpsert(BaseModel):
    profile: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    token_endpoint: Optional[str] = None
    app_id: Optional[int] = None


@router.get("/admin/tokens")
def list_tokens(_: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        rows = s.query(Token).order_by(Token.updated_at.desc()).all()
        return {"items": [
            {"id": x.id, "profile": x.profile, "tenant_id": x.tenant_id, "client_id": x.client_id, "expires_at": x.expires_at}
            for x in rows
        ]}


@router.get("/admin/tokens/by-profile/{profile}")
def get_token_by_profile(profile: str, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        x = s.query(Token).filter(Token.profile == profile).first()
        if not x:
            raise HTTPException(status_code=404, detail="not found")
        return {
            "id": x.id,
            "profile": x.profile,
            "tenant_id": x.tenant_id,
            "client_id": x.client_id,
            "scope": x.scope,
            "expires_at": x.expires_at,
            "token_endpoint": x.token_endpoint,
            "has_refresh": bool(x.refresh_token),
        }


@router.post("/admin/tokens")
def upsert_token(data: TokenUpsert, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        row = None
        if data.profile:
            row = s.query(Token).filter(Token.profile == data.profile).first()
        if not row:
            row = Token()
        for f in ("profile", "tenant_id", "client_id", "client_secret", "scope", "access_token", "refresh_token", "expires_at", "token_endpoint", "app_id"):
            setattr(row, f, getattr(data, f))
        s.add(row)
        s.flush()
        return {"id": row.id, "profile": row.profile}


class TokenFromAuth(BaseModel):
    profile: str
    app_id: Optional[int] = None


def _jwt_payload(tok: str) -> Dict[str, Any]:
    try:
        parts = tok.split(".")
        if len(parts) < 2:
            return {}
        pad = '=' * (-len(parts[1]) % 4)
        raw = base64.urlsafe_b64decode(parts[1] + pad)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


@router.post("/admin/tokens/from_auth")
def upsert_token_from_auth(data: TokenFromAuth, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    meta = get_current_user_meta() or {}
    g = (meta.get("graph") or {})
    at = g.get("access_token")
    rt = g.get("refresh_token")
    if not at:
        raise HTTPException(status_code=400, detail="No graph_access_token in admin token")
    claims = _jwt_payload(at)
    tenant_id = claims.get("tid") or claims.get("tenant")
    exp = claims.get("exp")
    token_endpoint = None
    if tenant_id:
        token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    with get_session() as s:
        row = s.query(Token).filter(Token.profile == data.profile).first() or Token()
        row.profile = data.profile
        row.tenant_id = tenant_id or row.tenant_id
        row.access_token = at
        row.refresh_token = rt or row.refresh_token
        row.expires_at = exp or row.expires_at
        row.token_endpoint = token_endpoint or row.token_endpoint
        row.app_id = data.app_id or row.app_id
        s.add(row)
        s.flush()
        return {"id": row.id, "profile": row.profile, "tenant_id": row.tenant_id, "expires_at": row.expires_at}


class ApiKeyCreate(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    groups: Optional[List[str]] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    app_id: Optional[int] = None


@router.get("/admin/api-keys")
def list_api_keys(_: None = Depends(dep_require_master)) -> Dict[str, Any]:
    with get_session() as s:
        rows = s.query(ApiKey).order_by(ApiKey.updated_at.desc()).all()
        return {"items": [
            {"key": x.key, "user_id": x.user_id, "name": x.name, "role": x.role, "token_profile": x.token_profile, "token_id": x.token_id, "enabled": x.enabled}
            for x in rows
        ]}


@router.post("/admin/api-keys")
def create_api_key(data: ApiKeyCreate, _: None = Depends(dep_require_master)) -> Dict[str, Any]:
    key = secrets.token_urlsafe(32)
    with get_session() as s:
        row = ApiKey(
            key=key,
            user_id=data.user_id,
            name=data.name,
            role=data.role,
            groups=(data.groups or []),
            token_profile=data.token_profile,
            token_id=data.token_id,
            app_id=data.app_id,
            enabled=True,
        )
        s.add(row)
        s.flush()
        return {"key": row.key}
