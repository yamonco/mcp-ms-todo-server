from __future__ import annotations
from fastapi import APIRouter, Depends
from app.api.security import dep_require_master
from app.schemas.admin import CasbinRulePayload, PolicyRulesResponse, ReloadResponse
from app.repositories import casbin_policies as casbin_repo
from app import policy as policy_mod


router = APIRouter(prefix="", tags=["admin:policy"], dependencies=[Depends(dep_require_master)])


@router.post("/policy/reload", response_model=ReloadResponse)
def policy_reload():
    ok = policy_mod.reload()
    return ReloadResponse(reloaded=bool(ok), note=None if ok else "Casbin not configured or reload failed")


@router.get("/policy/rules", response_model=PolicyRulesResponse)
def policy_rules_list():
    return {"rules": casbin_repo.list_rules()}  # type: ignore


@router.post("/policy/rules")
def policy_rules_add(payload: CasbinRulePayload):
    casbin_repo.add_rule(payload.ptype, payload.v0, payload.v1, payload.v2, payload.v3, payload.v4, payload.v5)
    policy_mod.reload()
    return {"ok": True}


@router.delete("/policy/rules")
def policy_rules_delete(payload: CasbinRulePayload):
    deleted = casbin_repo.delete_rule(payload.ptype, payload.v0, payload.v1, payload.v2, payload.v3, payload.v4, payload.v5)
    policy_mod.reload()
    return {"deleted": deleted}
