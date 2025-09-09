from typing import Optional
from app.context import get_current_user_meta
from app.config import cfg


class AuthentikTokenProvider:
    def __init__(self) -> None:
        pass

    def get_token(self) -> str:
        meta = get_current_user_meta() or {}
        g = meta.get("graph") or {}
        at = g.get("access_token")
        if at:
            return at
        if cfg.authentik_only:
            tok = meta.get("authentik_access_token")
            if tok:
                return tok
        raise RuntimeError("Graph access token not available (AUTHENTIK_ONLY requires graph_access_token claim)")

