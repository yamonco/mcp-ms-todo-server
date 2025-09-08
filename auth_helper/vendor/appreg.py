from __future__ import annotations
import time
from typing import Optional
try:
    from .config import Settings
    from .graph import get_admin_access_token, graph_request
    from . import dbsync
except Exception:  # pragma: no cover
    from config import Settings  # type: ignore
    from graph import get_admin_access_token, graph_request  # type: ignore
    import dbsync  # type: ignore


def _reuse_by_client_id(cfg: Settings, admin_token: str, desired_scopes: str) -> Optional[tuple[str, str, str]]:
    pre = (cfg.client_id or "").strip()
    if not pre:
        return None
    data = graph_request("GET", "/applications", token=admin_token, params={"$filter": f"appId eq '{pre}'"})
    if isinstance(data.get("value"), list) and data["value"]:
        tenant_id = cfg.admin_tenant_id or cfg.tenant_id
        cfg.client_id = pre
        cfg.tenant_id = tenant_id
        cfg.scopes = desired_scopes.split()
        ok = dbsync.upsert_app(cfg, tenant_id=tenant_id, client_id=pre, scopes=desired_scopes, display_name=None)
        if ok and dbsync.verify_app_saved(cfg):
            print(f"[DB] Meta saved (profile={cfg.app_profile})")
        else:
            print("[WARN] Failed to verify DB meta: check MCP_URL/ADMIN_API_KEY/TOKEN_PROFILE/permissions")
        return pre, tenant_id, desired_scopes
    print(f"[INFO] CLIENT_ID={pre} not found, searching/creating")
    return None


def _reuse_by_prefix(cfg: Settings, admin_token: str, desired_scopes: str) -> Optional[tuple[str, str, str]]:
    q = {"$filter": f"startsWith(displayName,'{cfg.app_prefix}')", "$orderby": "createdDateTime desc", "$top": 1}
    try:
        res = graph_request("GET", "/applications", token=admin_token, params=q)
        items = res.get("value", []) if isinstance(res, dict) else []
        if items:
            cand_id = items[0].get("appId")
            if cand_id:
                tenant_id = cfg.admin_tenant_id or cfg.tenant_id
                cfg.client_id = cand_id
                cfg.tenant_id = tenant_id
                cfg.scopes = desired_scopes.split()
                ok = dbsync.upsert_app(cfg, tenant_id=tenant_id, client_id=cand_id, scopes=desired_scopes, display_name=None)
                if ok and dbsync.verify_app_saved(cfg):
                    print(f"[DB] Meta saved (profile={cfg.app_profile})")
                else:
                    print("[WARN] Failed to verify DB meta: check MCP_URL/ADMIN_API_KEY/TOKEN_PROFILE/permissions")
                print(f"[REUSE] CLIENT_ID={cand_id}")
                return cand_id, tenant_id, desired_scopes
    except Exception as e:
        print(f"[INFO] App search failed: {e}")
    return None


def _create_app(cfg: Settings, admin_token: str, desired_scopes: str) -> tuple[str, str, str]:
    graph_app_id = "00000003-0000-0000-c000-000000000000"  # Microsoft Graph
    tasks_readwrite_scope = "2219042f-cab5-40cc-b0d2-16b1540b4c5f"  # Delegated Scope
    app_name = f"{cfg.app_prefix}-{int(time.time())}"
    body = {
        "displayName": app_name,
        "isFallbackPublicClient": True,
        "requiredResourceAccess": [
            {
                "resourceAppId": graph_app_id,
                "resourceAccess": [
                    {"id": tasks_readwrite_scope, "type": "Scope"}
                ],
            }
        ],
    }
    created = graph_request("POST", "/applications", token=admin_token, json_body=body)
    client_id = created.get("appId")
    tenant_id = cfg.admin_tenant_id or cfg.tenant_id
    cfg.client_id = client_id
    cfg.tenant_id = tenant_id
    cfg.scopes = desired_scopes.split()
    ok = dbsync.upsert_app(cfg, tenant_id=tenant_id, client_id=client_id, scopes=desired_scopes, display_name=app_name)
    if ok and dbsync.verify_app_saved(cfg):
        print(f"[DB] Meta saved (profile={cfg.app_profile})")
    else:
        print("[WARN] Failed to verify DB meta: check MCP_URL/ADMIN_API_KEY/TOKEN_PROFILE/permissions")
    print(f"CLIENT_ID={client_id}")
    print(f"TENANT_ID={tenant_id}")
    print(f"SCOPES={desired_scopes}")
    print("[DONE] (Graph) App registered and meta saved")
    return client_id, tenant_id, desired_scopes


def register_app(cfg: Settings, *, interactive: bool = False) -> tuple[str, str, str]:
    desired_scopes = "Tasks.ReadWrite"
    # Pre-check: if DB already has app meta for this profile, reuse it
    try:
        existing = dbsync.get_app_by_profile(cfg) or {}
        ex_client = (existing.get("client_id") or "").strip()
        ex_tenant = (existing.get("tenant_id") or "").strip()
        ex_scopes = (existing.get("scopes") or desired_scopes).strip() or desired_scopes
        if ex_client and ex_tenant:
            print(f"[INFO] App meta already present in DB (profile={cfg.app_profile}). Reusing.")
            # Ensure local cfg mirrors DB values for consistency
            cfg.client_id = ex_client
            cfg.tenant_id = ex_tenant
            cfg.scopes = ex_scopes.split()
            return ex_client, ex_tenant, ex_scopes
    except Exception as e:
        print(f"[INFO] DB pre-check failed (continuing): {e}")
    # If env already provides app meta, just copy to DB and return
    if (cfg.client_id or "").strip() and (cfg.tenant_id or "").strip():
        ok = dbsync.upsert_app(cfg, tenant_id=cfg.tenant_id, client_id=cfg.client_id, scopes=desired_scopes, display_name=None)
        if ok and dbsync.verify_app_saved(cfg):
            print(f"[DB] App meta copied (profile={cfg.app_profile})")
        else:
            print("[WARN] Failed to verify DB app meta copy. Check MCP_URL/ADMIN_API_KEY/TOKEN_PROFILE/permissions")
        return cfg.client_id, cfg.tenant_id, desired_scopes
    admin_token = get_admin_access_token(cfg, interactive=interactive)
    if interactive:
        print("[INFO] --interactive mode: admin sign-in for app registration")
    reused = _reuse_by_client_id(cfg, admin_token, desired_scopes)
    if reused:
        print(f"[REUSE] Existing app CLIENT_ID={reused[0]}")
        return reused
    reused = _reuse_by_prefix(cfg, admin_token, desired_scopes)
    if reused:
        return reused
    return _create_app(cfg, admin_token, desired_scopes)
# moved to auth_helper/vendor
