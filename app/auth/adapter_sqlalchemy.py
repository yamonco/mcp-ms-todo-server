from __future__ import annotations
"""SQLAlchemy adapter for Casbin (read-only load from casbin_rule)."""
try:
    from casbin import persist  # type: ignore
except Exception:  # pragma: no cover
    persist = None  # type: ignore

from app.db import get_session
from app.models import CasbinRule


class SqlAlchemyAdapter:  # implements casbin.persist.adapter.Adapter (load-policy only)
    def __init__(self):
        if persist is None:
            raise RuntimeError("casbin not installed")

    def load_policy(self, model) -> None:  # type: ignore[no-redef]
        from casbin.persist import load_policy_line  # type: ignore
        with get_session() as s:
            rows = s.query(CasbinRule).all()
            for r in rows:
                parts = [r.ptype]
                for v in (r.v0, r.v1, r.v2, r.v3, r.v4, r.v5):
                    if v is not None and v != "":
                        parts.append(v)
                line = ", ".join(parts)
                load_policy_line(line, model)

    # Write methods not implemented yet
    def save_policy(self, model) -> None:  # type: ignore[no-redef]
        raise NotImplementedError

    def add_policy(self, sec, ptype, rule):  # type: ignore[no-redef]
        raise NotImplementedError

    def remove_policy(self, sec, ptype, rule):  # type: ignore[no-redef]
        raise NotImplementedError

    def remove_filtered_policy(self, sec, ptype, field_index, *field_values):  # type: ignore[no-redef]
        raise NotImplementedError

