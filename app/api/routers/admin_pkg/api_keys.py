from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.admin import ErrorResponse

from app.api.security import dep_require_master
from app.apikeys import (
    generate_api_key,
    list_keys as apikey_list,
    delete_key as apikey_delete,
    list_users as apikey_users,
    update_key as apikey_update,
)
from app.schemas.admin import CreateKeyPayload, UpdateKeyPayload, CreateKeyResponse, ApiKeysResponse, DeleteResponse


router = APIRouter(prefix="", tags=["admin:api-keys"], dependencies=[Depends(dep_require_master)])


@router.post(
    "/api-keys",
    response_model=CreateKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Master API key required"},
    },
)
def create_api_key(payload: CreateKeyPayload):
    key, meta = generate_api_key(
        payload.template,
        allowed_tools=payload.allowed_tools,
        note=payload.note,
        user_id=payload.user_id,
        name=payload.name,
        token_profile=payload.token_profile,
        token_id=payload.token_id,
        role=payload.role,
        app_id=payload.app_id,
        app_profile=payload.app_profile,
        groups=payload.groups,
    )
    return {"api_key": key, "meta": meta}


@router.get("/api-keys", response_model=ApiKeysResponse)
def list_api_keys():
    return apikey_list()  # type: ignore


@router.delete(
    "/api-keys/{key}",
    response_model=DeleteResponse,
    responses={404: {"model": ErrorResponse, "description": "Key not found"}},
)
def delete_api_key(key: str):
    ok = apikey_delete(key)
    if not ok:
        raise HTTPException(status_code=404, detail="key not found")
    return {"deleted": True}


@router.patch("/api-keys/{key}", response_model=CreateKeyResponse)
def update_api_key(key: str, payload: UpdateKeyPayload):
    meta = apikey_update(key, payload.model_dump())
    if not meta:
        raise HTTPException(status_code=404, detail="key not found")
    return {"api_key": key, "meta": meta}


@router.post("/users", response_model=CreateKeyResponse)
def create_user(payload: CreateKeyPayload):
    return create_api_key(payload)


@router.get("/users")
def list_users():
    return apikey_users()
