from __future__ import annotations
import os
from dataclasses import dataclass
# moved to auth_helper/vendor


@dataclass
class Settings:
    # Server (Admin API)
    mcp_url: str
    api_key: str
    token_profile: str  # for user token ops (backward compatible)
    app_profile: str    # admin/app profile for app meta

    # App meta
    tenant_id: str
    client_id: str
    scopes: list[str]
    app_prefix: str

    # Refresh
    refresh_interval: int
    refresh_slack: int

    # Admin app creds (Graph)
    admin_tenant_id: str | None
    admin_client_id: str | None
    admin_client_secret: str | None

    @staticmethod
    def load() -> "Settings":
        mcp_url = (os.getenv("MCP_URL") or "http://localhost:8081").rstrip("/")
        # Admin key: prefer ADMIN_API_KEY; fallback to API_KEY for backward compatibility
        api_key = os.getenv("ADMIN_API_KEY", "") or os.getenv("API_KEY", "")
        token_profile = os.getenv("TOKEN_PROFILE") or os.getenv("USER") or "default"
        app_profile = os.getenv("APP_PROFILE") or os.getenv("ADMIN_PROFILE") or os.getenv("TOKEN_PROFILE") or "admin"

        tenant_id = os.getenv("TENANT_ID", "organizations")
        client_id = os.getenv("CLIENT_ID", "")
        scopes_raw = os.getenv("SCOPES", "Tasks.ReadWrite")
        scopes = [s for s in scopes_raw.split() if s]
        app_prefix = os.getenv("APP_PREFIX", "mcp-todo-server")

        refresh_interval = int(os.getenv("REFRESH_INTERVAL", "60"))
        refresh_slack = int(os.getenv("REFRESH_SLACK", "600"))

        admin_tenant_id = os.getenv("ADMIN_TENANT_ID")
        admin_client_id = os.getenv("ADMIN_CLIENT_ID")
        admin_client_secret = os.getenv("ADMIN_CLIENT_SECRET")

        return Settings(
            mcp_url=mcp_url,
            api_key=api_key,
            token_profile=token_profile,
            app_profile=app_profile,
            tenant_id=tenant_id,
            client_id=client_id,
            scopes=scopes,
            app_prefix=app_prefix,
            refresh_interval=refresh_interval,
            refresh_slack=refresh_slack,
            admin_tenant_id=admin_tenant_id,
            admin_client_id=admin_client_id,
            admin_client_secret=admin_client_secret,
        )
