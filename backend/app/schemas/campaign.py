"""Campaign schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class CampaignResponse(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    platform: str
    objective: Optional[str]
    campaign_type: Optional[str]
    status: str
    daily_budget: float
    platform_campaign_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    campaigns: List[CampaignResponse]
    total: int


class OptimizationLogResponse(BaseModel):
    id: UUID
    client_id: UUID
    campaign_id: Optional[UUID]
    action: str
    reason: Optional[str]
    entity_type: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
