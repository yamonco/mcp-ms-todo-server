from typing import Dict, Any, Optional
from app.db import get_session
from app.models import App


def list_apps() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    with get_session() as s:
        for a in s.query(App).all():
            out[str(a.id)] = {
                "profile": a.profile or "",
                "display_name": a.display_name or "",
                "tenant_id": a.tenant_id or "",
                "client_id": a.client_id or "",
                "scopes": a.scopes or "",
            }
    return out


def upsert_app(*, profile: str, tenant_id: str, client_id: str, scopes: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    with get_session() as s:
        rec = s.query(App).filter(App.profile == profile).first()
        if not rec:
            rec = App(profile=profile)
            s.add(rec)
        rec.display_name = display_name or rec.display_name
        rec.tenant_id = tenant_id
        rec.client_id = client_id
        rec.scopes = scopes
        s.flush()
        return {"id": rec.id, "profile": rec.profile}


def get_app_by_profile(profile: str) -> Optional[Dict[str, Any]]:
    with get_session() as s:
        a = s.query(App).filter(App.profile == profile).first()
        if not a:
            return None
        return {
            "id": a.id,
            "profile": a.profile,
            "display_name": a.display_name,
            "tenant_id": a.tenant_id,
            "client_id": a.client_id,
            "scopes": a.scopes,
        }

