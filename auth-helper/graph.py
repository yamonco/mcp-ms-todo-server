from __future__ import annotations
import time
import requests
from typing import Optional, Dict, Any
from .config import Settings


def get_admin_access_token(cfg: Settings, *, interactive: bool = False) -> str:
    """관리자(Graph) 액세스 토큰 발급.
    - 기본: 클라이언트 크리덴셜(Application.ReadWrite.All 권한 필요)
    - interactive=True 인 경우에만 디바이스 코드 흐름으로 대체(선택)
    """
    tenant = cfg.admin_tenant_id or cfg.tenant_id
    cid = cfg.admin_client_id
    secret = cfg.admin_client_secret

    if tenant and cid and secret and not interactive:
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": cid,
            "client_secret": secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        }
        r = requests.post(token_url, data=data, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"관리자 토큰 발급 실패: {r.status_code} {r.text[:200]}")
        return r.json().get("access_token", "")

    if not interactive:
        raise RuntimeError("ADMIN_* credentials missing. Use --interactive to sign in as an admin.")

    # Optional interactive device-code flow (admin only)
    device_code_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    public_client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Microsoft official public client
    scope = "https://graph.microsoft.com/.default offline_access"
    resp = requests.post(device_code_url, data={"client_id": public_client_id, "scope": scope}, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Device code request failed: {resp.status_code} {resp.text[:200]}")
    dc = resp.json()
    print(f"[Sign-in] {dc.get('message', '')}")
    interval = int(dc.get("interval", 5))
    expires = int(dc.get("expires_in", 900))
    start = time.time()
    while True:
        if time.time() - start > expires:
            raise RuntimeError("Device code expired")
        time.sleep(interval)
        poll = requests.post(token_url, data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": public_client_id,
            "device_code": dc["device_code"],
        }, timeout=10)
        if poll.status_code == 200:
            tok = poll.json()
            print("[Sign-in success]")
            return tok["access_token"]
        elif poll.status_code in (400, 401):
            err = poll.json().get("error", "")
            if err in ("authorization_pending", "slow_down"):
                continue
            raise RuntimeError(f"Sign-in failed: {poll.text}")
        else:
            raise RuntimeError(f"Sign-in failed: {poll.status_code} {poll.text}")


def graph_request(method: str, path: str, *, token: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    url = f"https://graph.microsoft.com/v1.0{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    func = requests.get if method.upper() == "GET" else requests.post if method.upper() == "POST" else requests.patch
    r = func(url, headers=headers, json=json_body, params=params, timeout=20)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Graph {method} {path} 실패: {r.status_code} {r.text[:200]}")
    return r.json()
