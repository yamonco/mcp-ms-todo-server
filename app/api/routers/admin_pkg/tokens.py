from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.api.security import dep_require_master
from app.schemas.admin import UpsertTokenPayload, TokensResponse, TokenInfo
from app.tokens import list_tokens as token_list, upsert_token as token_upsert, get_token_by_profile


router = APIRouter(prefix="", tags=["admin:tokens"], dependencies=[Depends(dep_require_master)])


@router.get("/tokens", response_model=TokensResponse)
def list_tokens():
    return token_list()  # type: ignore


@router.post("/tokens", response_model=TokenInfo)
def upsert_token(payload: UpsertTokenPayload):
    return token_upsert(
        profile=payload.profile,
        token_data=payload.token,
        tenant_id=payload.tenant_id,
        client_id=payload.client_id,
        scopes=payload.scopes,
    )


@router.get("/tokens/by-profile/{profile}", response_model=TokenInfo)
def read_token_by_profile(profile: str):
    data = get_token_by_profile(profile)  # type: ignore
    if not data:
        raise HTTPException(status_code=404, detail="token not found")
    return data
