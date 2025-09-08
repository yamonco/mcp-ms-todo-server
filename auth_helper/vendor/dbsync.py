from __future__ import annotations
from typing import Optional, Dict, Any
import requests
from .config import Settings


def upsert_token(cfg: Settings, token: Dict[str, Any]) -> bool:
    if not (cfg.mcp_url and cfg.api_key and cfg.token_profile):
        print("[DB] Upsert skipped: missing MCP_URL/ADMIN_API_KEY/TOKEN_PROFILE.\n"
              "      - MCP_URL (e.g., http://localhost:8081)\n"
              "      - ADMIN_API_KEY (master key; set in .env)\n"
              "      - TOKEN_PROFILE (e.g., admin)", flush=True)
        return False
    try:
        url = f"{cfg.mcp_url}/admin/tokens"
        body = {
            "profile": cfg.token_profile,
            "token": token,
            "tenant_id": cfg.tenant_id,
            "client_id": cfg.client_id,
            "scopes": " ".join(cfg.scopes),
        }
        r = requests.post(url, headers={"x-api-key": cfg.api_key}, json=body, timeout=10)
        if r.status_code not in (200, 201):
            print(f"[DB] Token upsert failed: {r.status_code} {r.text[:200]}", flush=True)
            return False
        return True
    except Exception as e:
        print(f"[DB] Token upsert error: {e}", flush=True)
        return False


def get_token_by_profile(cfg: Settings) -> Optional[Dict[str, Any]]:
    try:
        url = f"{cfg.mcp_url}/admin/tokens/by-profile/{cfg.token_profile}"
        r = requests.get(url, headers={"x-api-key": cfg.api_key}, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None
# moved to auth_helper/vendor


# Apps admin API
def upsert_app(cfg: Settings, *, tenant_id: str, client_id: str, scopes: str, display_name: Optional[str] = None) -> bool:
    if not (cfg.mcp_url and cfg.api_key and cfg.app_profile):
        print("[DB] Upsert app skipped: missing MCP_URL/ADMIN_API_KEY/APP_PROFILE.")
        return False
    try:
        url = f"{cfg.mcp_url}/admin/apps"
        body = {
            "profile": cfg.app_profile,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "scopes": scopes,
            "display_name": display_name,
        }
        r = requests.post(url, headers={"x-api-key": cfg.api_key}, json=body, timeout=10)
        if r.status_code not in (200, 201):
            print(f"[DB] App upsert failed: {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[DB] App upsert error: {e}")
        return False


def get_app_by_profile(cfg: Settings) -> Optional[Dict[str, Any]]:
    if not (cfg.mcp_url and cfg.api_key and cfg.app_profile):
        return None
    try:
        url = f"{cfg.mcp_url}/admin/apps/by-profile/{cfg.app_profile}"
        r = requests.get(url, headers={"x-api-key": cfg.api_key}, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def verify_app_saved(cfg: Settings) -> bool:
    data = get_app_by_profile(cfg) or {}
    return bool((data.get("client_id") or "") == (cfg.client_id or "") and (data.get("tenant_id") or "") == (cfg.tenant_id or ""))


def verify_meta_saved(cfg: Settings) -> bool:
    data = get_token_by_profile(cfg) or {}
    return bool(data.get("client_id") == cfg.client_id and data.get("tenant_id") == cfg.tenant_id)
