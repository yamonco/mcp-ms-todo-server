from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class ToolInputSchema(BaseModel):
    type: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None
    additionalProperties: Optional[bool] = None


class ToolDef(BaseModel):
    name: str
    description: Optional[str] = None
    inputSchema: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema for input")


class ManifestResponse(BaseModel):
    tools: List[ToolDef]


class JsonRpcErrorObj(BaseModel):
    code: int
    message: str


class JsonRpcSuccess(BaseModel):
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Any] = Field(default=None, description="Request id (string/number/null)")
    result: Dict[str, Any] = Field(description="JSON-RPC success result")


class JsonRpcError(BaseModel):
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Any] = Field(default=None, description="Request id (string/number/null)")
    error: JsonRpcErrorObj = Field(description="JSON-RPC error object")


JsonRpcEnvelope = Union[JsonRpcSuccess, JsonRpcError]
