from __future__ import annotations
"""Synchronize group tool mappings into Casbin policies.

For each group, we create p, group:<name>, <tool>, use entries in casbin_rule.
On delete, we remove entries for that group.
"""
from typing import Optional
from app.db import get_session
from app.models import GroupTool, CasbinRule


def sync_group(name: Optional[str] = None) -> None:
    with get_session() as s:
        if name:
            # remove existing rules for this group
            s.query(CasbinRule).filter(CasbinRule.ptype == "p", CasbinRule.v0 == f"group:{name}").delete(synchronize_session=False)
            tools = [gt.tool for gt in s.query(GroupTool).filter(GroupTool.group == name).all()]
            for t in tools:
                s.add(CasbinRule(ptype="p", v0=f"group:{name}", v1=t, v2="use"))
            return
        # full resync
        # clear all group:* entries
        s.query(CasbinRule).filter(CasbinRule.ptype == "p", CasbinRule.v0.like("group:%")).delete(synchronize_session=False)
        rows = s.query(GroupTool).all()
        for gt in rows:
            s.add(CasbinRule(ptype="p", v0=f"group:{gt.group}", v1=gt.tool, v2="use"))


def delete_group(name: str) -> None:
    with get_session() as s:
        s.query(CasbinRule).filter(CasbinRule.ptype == "p", CasbinRule.v0 == f"group:{name}").delete(synchronize_session=False)

