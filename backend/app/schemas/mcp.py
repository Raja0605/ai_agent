from typing import Any, List, Optional
from datetime import date
from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    name: str
    server_type: str = "job-search"
    transport: str = Field(pattern="^(stdio|sse|streamable-http)$")
    endpoint: str
    enabled: bool = True


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    endpoint: Optional[str] = None
    enabled: Optional[bool] = None
    transport: Optional[str] = Field(default=None, pattern="^(stdio|sse|streamable-http)$")


class MCPServerResponse(MCPServerCreate):
    id: str
    status: str
    class Config: from_attributes = True


class MCPSearchRequest(BaseModel):
    server_ids: List[str]
    keywords: List[str] = Field(min_length=1)
    location: Optional[str] = None
    remote: Optional[bool] = None
    experience_min: Optional[int] = Field(default=None, ge=0, le=60)
    experience_max: Optional[int] = Field(default=None, ge=0, le=60)
    posted_after: Optional[date] = None
    posted_before: Optional[date] = None
    limit: int = Field(default=25, ge=1, le=100)
