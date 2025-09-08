from __future__ import annotations
from .loader import load_helper_module

_mod = load_helper_module("config")
Settings = _mod.Settings  # re-export

