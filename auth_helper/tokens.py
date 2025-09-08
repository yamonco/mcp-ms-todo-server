from __future__ import annotations
from .loader import load_helper_module

_mod = load_helper_module("tokens")

save_token = getattr(_mod, "save_token")

