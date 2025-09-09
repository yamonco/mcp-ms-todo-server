from __future__ import annotations
import os
import time
from typing import Optional

import requests

_CACHE: dict[str, tuple[bool, float]] = {}


def _cache_key(tenant_id: str | None, user_id: str | None) -> str:
    return f"{tenant_id or ''}:{user_id or ''}"


def verify_license(tenant_id: Optional[str], user_id: Optional[str]) -> bool:
    enabled = os.getenv("SAAS_ENABLED", "").lower() in {"1", "true", "yes"}
    if not enabled:
        return True
    verify_url = os.getenv("LICENSE_VERIFY_URL")
    if not verify_url:
        # fail closed if enabled but no endpoint
        return False
    key = _cache_key(tenant_id, user_id)
    now = time.time()
    cached = _CACHE.get(key)
    if cached and (now - cached[1]) < int(os.getenv("LICENSE_CACHE_TTL", "60")):
        return cached[0]
    try:
        payload = {"tenant_id": tenant_id, "user_id": user_id}
        r = requests.post(verify_url, json=payload, timeout=5)
        ok = r.status_code == 200 and (r.json() or {}).get("ok") is True
        _CACHE[key] = (ok, now)
        return ok
    except Exception:
        return False

