from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.api.security import dep_require_master
from app.schemas.admin import UpsertAppPayload, AppsResponse, AppInfo
from app.apps import list_apps as app_list, upsert_app as app_upsert, get_app_by_profile as app_get


router = APIRouter(prefix="", tags=["admin:apps"], dependencies=[Depends(dep_require_master)])


@router.get("/apps", response_model=AppsResponse)
def list_apps():
    return app_list()  # type: ignore


@router.get("/apps/by-profile/{profile}", response_model=AppInfo)
def get_app(profile: str):
    data = app_get(profile)  # type: ignore
    if not data:
        raise HTTPException(status_code=404, detail="app not found")
    return data


@router.post("/apps", response_model=AppInfo)
def upsert_app(payload: UpsertAppPayload):
    return app_upsert(
        profile=payload.profile,
        tenant_id=payload.tenant_id,
        client_id=payload.client_id,
        scopes=payload.scopes,
        display_name=payload.display_name,
    )
