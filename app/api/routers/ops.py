from __future__ import annotations
from fastapi import APIRouter, Depends
from app.api.security import dep_require_master
from app import policy as policy_mod


router = APIRouter()


@router.post("/ops/policy/reload")
def ops_policy_reload(_: None = Depends(dep_require_master)):
    ok = policy_mod.reload()
    return {"reloaded": bool(ok)}

