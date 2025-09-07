from typing import Optional
from app.db import get_session
from app.models import Token


class DBTokenProvider:
    def __init__(self, *, token_id: Optional[int] = None, profile: Optional[str] = None):
        self.token_id = token_id
        self.profile = profile

    def _fetch(self) -> Optional[Token]:
        with get_session() as s:
            if self.token_id is not None:
                return s.get(Token, self.token_id)
            if self.profile:
                return s.query(Token).filter(Token.profile == self.profile).first()
            return None

    def get_token(self) -> str:
        t = self._fetch()
        return (t.access_token or "") if t else ""
