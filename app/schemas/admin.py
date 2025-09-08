from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from pydantic import RootModel


class CreateKeyPayload(BaseModel):
    template: str
    allowed_tools: Optional[List[str]] = None
    note: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    role: Optional[str] = None
    app_id: Optional[int] = None
    app_profile: Optional[str] = None
    groups: Optional[List[str]] = None


class UpdateKeyPayload(BaseModel):
    template: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    note: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    role: Optional[str] = None
    app_id: Optional[int] = None
    groups: Optional[List[str]] = None


class UpsertTokenPayload(BaseModel):
    profile: Optional[str] = None
    token: Dict[str, Any]
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None


class GroupPayload(BaseModel):
    tools: List[str] = []
    tags: List[str] = []


class UpsertAppPayload(BaseModel):
    profile: Optional[str] = None
    display_name: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None


class CasbinRulePayload(BaseModel):
    ptype: str
    v0: Optional[str] = None
    v1: Optional[str] = None
    v2: Optional[str] = None
    v3: Optional[str] = None
    v4: Optional[str] = None
    v5: Optional[str] = None


# ---- Response models (minimal) ----
class ApiKeyMeta(BaseModel):
    template: str
    allowed_tools: Optional[List[str]] = None
    note: Optional[str] = None
    user_id: Optional[str] = None
    name: Optional[str] = None
    token_profile: Optional[str] = None
    token_id: Optional[int] = None
    role: Optional[str] = None
    app_id: Optional[int] = None
    groups: Optional[List[str]] = None


class CreateKeyResponse(BaseModel):
    api_key: str
    meta: ApiKeyMeta


class ApiKeysResponse(RootModel[Dict[str, ApiKeyMeta]]):
    pass


class DeleteResponse(BaseModel):
    deleted: bool


class ErrorResponse(BaseModel):
    detail: str


class GroupInfo(BaseModel):
    tools: List[str] = []
    tags: List[str] = []


class GroupsResponse(RootModel[Dict[str, GroupInfo]]):
    pass


class PolicyRule(BaseModel):
    ptype: str
    v0: Optional[str] = None
    v1: Optional[str] = None
    v2: Optional[str] = None
    v3: Optional[str] = None
    v4: Optional[str] = None
    v5: Optional[str] = None


class PolicyRulesResponse(BaseModel):
    rules: List[PolicyRule]


class ReloadResponse(BaseModel):
    reloaded: bool
    note: Optional[str] = None


# Tokens
class TokenInfo(BaseModel):
    id: Optional[int] = None
    profile: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_on: Optional[int] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None


class TokensResponse(RootModel[Dict[str, TokenInfo]]):
    pass


# Apps
class AppInfo(BaseModel):
    id: Optional[int] = None
    profile: Optional[str] = None
    display_name: Optional[str] = None
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: Optional[str] = None


class AppsResponse(RootModel[Dict[str, AppInfo]]):
    pass
