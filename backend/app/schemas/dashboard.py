"""Dashboard schemas."""

from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class MetricsSummary(BaseModel):
    total_spend: float = 0.0
    total_revenue: float = 0.0
    total_conversions: int = 0
    avg_roas: float = 0.0
    avg_cpa: float = 0.0
    avg_ctr: float = 0.0
    budget_usage_pct: float = 0.0
    monthly_budget: float = 0.0


class DailyMetricPoint(BaseModel):
    date: date
    spend: float = 0.0
    revenue: float = 0.0
    conversions: int = 0
    roas: float = 0.0
    cpa: float = 0.0
    clicks: int = 0
    impressions: int = 0


class DailyMetricsResponse(BaseModel):
    data: List[DailyMetricPoint]
    period_days: int


class TopCampaign(BaseModel):
    campaign_id: str
    name: str
    platform: str
    spend: float
    revenue: float
    roas: float
    conversions: int
    status: str


class DashboardOverview(BaseModel):
    summary: MetricsSummary
    daily_metrics: List[DailyMetricPoint]
    top_campaigns: List[TopCampaign]
    automation_status: str
    recent_actions: int
