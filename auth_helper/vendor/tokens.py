from __future__ import annotations
import time
import requests
from typing import Optional, Dict, Any
try:
from .config import Settings
from . import dbsync
# moved to auth_helper/vendor
except Exception:  # pragma: no cover
    from config import Settings  # type: ignore
    import dbsync  # type: ignore


def is_token_valid(access_token: str) -> bool:
    if not access_token:
        return False
    try:
        r = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _refresh_with_refresh_token(cfg: Settings, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rt = token.get("refresh_token")
    if not rt:
        return None
    tenant = cfg.tenant_id or "organizations"
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": cfg.client_id,
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "scope": " ".join(cfg.scopes) or "Tasks.ReadWrite",
    }
    try:
        resp = requests.post(url, data=data, timeout=15)
        if resp.status_code != 200:
            print(f"[REFRESH] Failed {resp.status_code}: {resp.text[:200]}")
            return None
        res = resp.json()
        if "expires_in" in res and "expires_on" not in res:
            try:
                res["expires_on"] = int(time.time()) + int(res.get("expires_in", 0))
            except Exception:
                pass
        return res
    except Exception as e:
        print(f"[REFRESH] Error: {e}")
        return None


def load_token(cfg: Settings) -> Optional[Dict[str, Any]]:
    data = dbsync.get_token_by_profile(cfg) or {}
    raw = data.get("raw") if isinstance(data, dict) else None
    if isinstance(raw, dict) and raw.get("access_token"):
        return raw
    # fallback to flattened
    if data.get("access_token"):
        return {k: data.get(k) for k in ("access_token", "refresh_token", "expires_on", "expires_in", "token_type", "scope")}
    return None


def save_token(cfg: Settings, token: Dict[str, Any]) -> bool:
    token_only = {k: v for k, v in token.items() if k in {"access_token", "refresh_token", "expires_on", "expires_in", "token_type", "scope"}}
    if "expires_in" in token_only and "expires_on" not in token_only:
        try:
            token_only["expires_on"] = int(time.time()) + int(token_only.get("expires_in", 0))
        except Exception:
            pass
    return dbsync.upsert_token(cfg, token_only)


def refresh_if_needed(cfg: Settings, slack_seconds: int) -> bool:
    token = load_token(cfg) or {}
    now = int(time.time())
    try:
        exp = int(token.get("expires_on", 0))
    except Exception:
        exp = 0
    if token.get("access_token") and exp and (exp - now) > slack_seconds:
        print("[REFRESH] Not needed (enough time left)")
        return True
    print("[REFRESH] Trying refresh_token grant")
    new_tok = _refresh_with_refresh_token(cfg, token)
    if new_tok and new_tok.get("access_token"):
        ok = save_token(cfg, new_tok)
        if ok:
            print("[REFRESH] Success via refresh_token")
            return True
    print("[REFRESH] Failed: refresh_token not usable")
    return False
