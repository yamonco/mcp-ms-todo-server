from __future__ import annotations
import importlib.util
import os
import types


def load_helper_module(name: str) -> types.ModuleType:
    base = os.path.join(os.path.dirname(__file__), "vendor")
    path = os.path.abspath(os.path.join(base, f"{name}.py"))
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"auth-helper module not found: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod
