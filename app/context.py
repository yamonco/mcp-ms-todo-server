from __future__ import annotations
from typing import Optional, Dict, Any
import contextvars


_api_key_meta: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar("api_key_meta", default=None)


def set_current_user_meta(meta: Optional[Dict[str, Any]]) -> None:
    _api_key_meta.set(meta)


def get_current_user_meta() -> Optional[Dict[str, Any]]:
    return _api_key_meta.get()

