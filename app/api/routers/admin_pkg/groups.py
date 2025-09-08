from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.api.security import dep_require_master
from app.schemas.admin import GroupPayload, GroupsResponse, DeleteResponse
from app.apikeys import list_groups as group_list, upsert_group as group_upsert, delete_group as group_delete
from app.services.policy_sync import sync_group, delete_group as sync_delete_group


router = APIRouter(prefix="", tags=["admin:groups"], dependencies=[Depends(dep_require_master)])


@router.get("/groups", response_model=GroupsResponse)
def groups_list():
    return group_list()  # type: ignore


@router.put("/groups/{name}", response_model=GroupsResponse)
def groups_put(name: str, payload: GroupPayload):
    out = group_upsert(name, payload.tools or [], payload.tags or [])
    try:
        sync_group(name)
    except Exception:
        pass
    return out


@router.delete("/groups/{name}", response_model=DeleteResponse)
def groups_del(name: str):
    ok = group_delete(name)
    if not ok:
        raise HTTPException(status_code=404, detail="group not found")
    try:
        sync_delete_group(name)
    except Exception:
        pass
    return {"deleted": True}
