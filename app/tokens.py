from typing import Dict, Any, Optional
from app.db import get_session
from app.models import Token


def list_tokens() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    with get_session() as s:
        for t in s.query(Token).all():
            out[str(t.id)] = {
                "profile": t.profile or "",
                "tenant_id": t.tenant_id or "",
                "client_id": t.client_id or "",
                "scopes": t.scopes or "",
                "has_refresh": bool(t.refresh_token),
                "expires_on": t.expires_on,
            }
    return out


def upsert_token(*, profile: Optional[str], token_data: Dict[str, Any], tenant_id: Optional[str] = None, client_id: Optional[str] = None, scopes: Optional[str] = None) -> Dict[str, Any]:
    # Extract common fields from token_data
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_on = token_data.get("expires_on")
    expires_in = token_data.get("expires_in")
    token_type = token_data.get("token_type")
    scope = token_data.get("scope")
    with get_session() as s:
        rec: Optional[Token] = None
        if profile:
            rec = s.query(Token).filter(Token.profile == profile).first()
        if not rec:
            rec = Token(profile=profile)
            s.add(rec)
        rec.access_token = access_token
        rec.refresh_token = refresh_token
        try:
            rec.expires_on = int(expires_on) if expires_on is not None else None
        except Exception:
            rec.expires_on = None
        rec.expires_in = int(expires_in) if isinstance(expires_in, int) else None
        rec.token_type = token_type
        rec.scope = scope
        if tenant_id is not None:
            rec.tenant_id = tenant_id
        if client_id is not None:
            rec.client_id = client_id
        if scopes is not None:
            rec.scopes = scopes
        s.flush()
        return {
            "id": rec.id,
            "profile": rec.profile,
        }


def get_token_by_profile(profile: str) -> Optional[Dict[str, Any]]:
    with get_session() as s:
        t = s.query(Token).filter(Token.profile == profile).first()
        if not t:
            return None
        return {
            "id": t.id,
            "profile": t.profile,
            "access_token": t.access_token,
            "refresh_token": t.refresh_token,
            "expires_on": t.expires_on,
            "expires_in": t.expires_in,
            "token_type": t.token_type,
            "scope": t.scope,
            "tenant_id": t.tenant_id,
            "client_id": t.client_id,
            "scopes": t.scopes,
        }
