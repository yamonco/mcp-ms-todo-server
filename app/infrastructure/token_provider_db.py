from __future__ import annotations
from typing import Optional
import time
import httpx

from app.db import get_session
from app.models import Token


class DBTokenProvider:
    """Token provider that loads tokens from DB by profile or id.
    Performs best-effort refresh if expired and refresh_token is present.
    """

    def __init__(self, *, token_profile: Optional[str] = None, token_id: Optional[int] = None):
        self.token_profile = token_profile
        self.token_id = token_id

    def _load(self) -> Token:
        with get_session() as s:
            q = s.query(Token)
            if self.token_id:
                t = q.filter(Token.id == self.token_id).first()
            else:
                t = q.filter(Token.profile == (self.token_profile or "")).first()
            if not t:
                raise RuntimeError("Token not found for API key")
            return t

    def _save(self, t: Token) -> None:
        from app.db import get_session as _gs
        with _gs() as s:
            s.merge(t)

    def _should_refresh(self, t: Token) -> bool:
        try:
            if not t.expires_at:
                return False
            # refresh slightly before expiry
            return int(time.time()) >= int(t.expires_at) - 60
        except Exception:
            return False

    def _refresh(self, t: Token) -> Optional[str]:
        if not (t.refresh_token and t.token_endpoint and t.client_id and t.client_secret):
            return None
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": t.refresh_token,
                "client_id": t.client_id,
                "client_secret": t.client_secret,
            }
            with httpx.Client(timeout=10) as c:
                r = c.post(t.token_endpoint, data=data)
                if r.status_code != 200:
                    return None
                js = r.json()
                t.access_token = js.get("access_token") or t.access_token
                t.refresh_token = js.get("refresh_token") or t.refresh_token
                if js.get("expires_in"):
                    t.expires_at = int(time.time()) + int(js.get("expires_in") or 0)
                self._save(t)
                return t.access_token
        except Exception:
            return None

    def get_token(self) -> str:
        t = self._load()
        if not t.access_token:
            raise RuntimeError("No access token stored")
        if self._should_refresh(t):
            newtok = self._refresh(t)
            return newtok or t.access_token
        return t.access_token

