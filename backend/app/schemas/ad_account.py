"""Ad Account schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class AdAccountResponse(BaseModel):
    id: UUID
    client_id: UUID
    platform: str
    account_id: str
    account_name: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthURLResponse(BaseModel):
    auth_url: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
