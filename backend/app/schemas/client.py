"""Client schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class ClientCreate(BaseModel):
    company_name: str
    website: Optional[str] = None
    country: str = "US"
    industry: Optional[str] = None
    monthly_budget: float = 0.0
    currency: str = "USD"


class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    monthly_budget: Optional[float] = None
    currency: Optional[str] = None
    # Ad Platform Credentials
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_developer_token: Optional[str] = None
    ga4_property_id: Optional[str] = None


class ClientResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_name: str
    website: Optional[str]
    country: str
    industry: Optional[str]
    monthly_budget: float
    currency: str
    automation_status: str
    is_active: bool
    # Ad Platform Credentials
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_developer_token: Optional[str] = None
    ga4_property_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetSettingsUpdate(BaseModel):
    monthly_cap: Optional[float] = None
    prospecting_pct: Optional[float] = None
    retargeting_pct: Optional[float] = None
    testing_pct: Optional[float] = None


class BudgetSettingsResponse(BaseModel):
    id: UUID
    client_id: UUID
    monthly_cap: float
    current_month_spend: float
    prospecting_pct: float
    retargeting_pct: float
    testing_pct: float

    class Config:
        from_attributes = True
