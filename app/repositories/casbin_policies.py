from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from app.db import get_session
from app.models import CasbinRule


def list_rules() -> List[Dict[str, Any]]:
    with get_session() as s:
        rows = s.query(CasbinRule).all()
        return [
            {
                "ptype": r.ptype,
                "v0": r.v0,
                "v1": r.v1,
                "v2": r.v2,
                "v3": r.v3,
                "v4": r.v4,
                "v5": r.v5,
            }
            for r in rows
        ]


def add_rule(ptype: str, v0: Optional[str] = None, v1: Optional[str] = None, v2: Optional[str] = None,
             v3: Optional[str] = None, v4: Optional[str] = None, v5: Optional[str] = None) -> None:
    with get_session() as s:
        s.add(CasbinRule(ptype=ptype, v0=v0, v1=v1, v2=v2, v3=v3, v4=v4, v5=v5))


def delete_rule(ptype: str, v0: Optional[str] = None, v1: Optional[str] = None, v2: Optional[str] = None,
                v3: Optional[str] = None, v4: Optional[str] = None, v5: Optional[str] = None) -> int:
    with get_session() as s:
        q = s.query(CasbinRule).filter(CasbinRule.ptype == ptype)
        if v0 is not None:
            q = q.filter(CasbinRule.v0 == v0)
        if v1 is not None:
            q = q.filter(CasbinRule.v1 == v1)
        if v2 is not None:
            q = q.filter(CasbinRule.v2 == v2)
        if v3 is not None:
            q = q.filter(CasbinRule.v3 == v3)
        if v4 is not None:
            q = q.filter(CasbinRule.v4 == v4)
        if v5 is not None:
            q = q.filter(CasbinRule.v5 == v5)
        return q.delete(synchronize_session=False)

