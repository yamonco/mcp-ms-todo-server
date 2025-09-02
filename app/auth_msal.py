import os, json, threading, time
from typing import Optional, Dict, Any
from pathlib import Path

import msal

CACHE_DIR = Path(os.getenv("TOKEN_CACHE_DIR", "/app/data/token_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "msal_token_cache.bin"

TENANT_ID = os.getenv("TENANT_ID", "organizations")
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SCOPES = (os.getenv("SCOPES", "Tasks.ReadWrite offline_access").split())

# Use a public client. If CLIENT_ID empty, msal requires an app id.
# We fall back to Microsoft "Developer Mode" public client id used by MSAL samples if none provided.
# It's better to set your own CLIENT_ID, but to minimize Azure setup, keep it optional.
DEFAULT_PUBLIC_CLIENT_ID = CLIENT_ID or "04f0c124-f2bc-4f59-8241-bf6df9866bbd"  # Microsoft official UWP/Dev sample client

_cache = msal.SerializableTokenCache()
if CACHE_FILE.exists():
    _cache.deserialize(CACHE_FILE.read_text())

def _persist_cache():
    CACHE_FILE.write_text(_cache.serialize())

_app = msal.PublicClientApplication(
    client_id=DEFAULT_PUBLIC_CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    token_cache=_cache
)

_device_flow_state: Dict[str, Any] = {}

def acquire_token_silent() -> Optional[Dict[str, Any]]:
    accounts = _app.get_accounts()
    if accounts:
        result = _app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache()
            return result
    return None

def start_device_code_flow() -> Dict[str, Any]:
    global _device_flow_state
    flow = _app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Failed to create device code flow")
    _device_flow_state = {"flow": flow, "started_at": time.time()}
    return {
        "user_code": flow["user_code"],
        "verification_uri": flow["verification_uri"],
        "message": flow.get("message"),
        "expires_in": flow.get("expires_in")
    }

def poll_device_code_flow(timeout: int = 900) -> Dict[str, Any]:
    global _device_flow_state
    if "flow" not in _device_flow_state:
        return {"status":"no_flow"}
    flow = _device_flow_state["flow"]
    result = _app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        _persist_cache()
        _device_flow_state = {}
        return {"status":"ok"}
    else:
        # msal handles polling inside acquire_token_by_device_flow; non-success returns error
        err = result.get("error_description") or str(result)
        return {"status":"error", "error": err}

def get_access_token(force_interactive: bool=False) -> Dict[str, Any]:
    if not force_interactive:
        silent = acquire_token_silent()
        if silent:
            return silent
    # No silent token, require device flow kickoff by client
    raise PermissionError("no_token: start device code flow via auth.start_device_code")

def logout() -> None:
    # Clear cache file
    try:
        CACHE_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    _cache.clear()
