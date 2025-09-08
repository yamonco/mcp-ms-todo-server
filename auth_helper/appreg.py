from __future__ import annotations
from .loader import load_helper_module

_mod = load_helper_module("appreg")

register_application = getattr(_mod, "register_application", None)

