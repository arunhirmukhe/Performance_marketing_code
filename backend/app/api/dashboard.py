"""Dashboard API routes - aggregated metrics and performance data."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta

from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.campaign import Campaign
from app.models.daily_metrics import DailyMetrics
from app.models.budget_settings import BudgetSettings
from app.models.optimization_log import OptimizationLog
from app.schemas.dashboard import MetricsSummary, DailyMetricPoint, DailyMetricsResponse, DashboardOverview, TopCampaign
from app.utils.security import get_current_user
from app.utils.helpers import safe_divide

router = APIRouter()


async def _get_client(user: User, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client).where(Client.user_id == user.id, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="No active client found")
    return client


@router.get("/metrics", response_model=MetricsSummary)
async def get_metrics_summary(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated metrics for the last N days."""
    client = await _get_client(current_user, db)
    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            func.coalesce(func.sum(DailyMetrics.spend), 0).label("total_spend"),
            func.coalesce(func.sum(DailyMetrics.revenue), 0).label("total_revenue"),
            func.coalesce(func.sum(DailyMetrics.conversions), 0).label("total_conversions"),
            func.coalesce(func.avg(DailyMetrics.ctr), 0).label("avg_ctr"),
        ).where(
            DailyMetrics.client_id == client.id,
            DailyMetrics.date >= start_date,
        )
    )
    row = result.one()

    total_spend = float(row.total_spend)
    total_revenue = float(row.total_revenue)
    total_conversions = int(row.total_conversions)

    # Budget usage
    budget_result = await db.execute(
        select(BudgetSettings).where(BudgetSettings.client_id == client.id)
    )
    budget = budget_result.scalar_one_or_none()
    monthly_budget = budget.monthly_cap if budget else 0
    budget_usage = safe_divide(budget.current_month_spend, monthly_budget) * 100 if budget else 0

    return MetricsSummary(
        total_spend=total_spend,
        total_revenue=total_revenue,
        total_conversions=total_conversions,
        avg_roas=safe_divide(total_revenue, total_spend),
        avg_cpa=safe_divide(total_spend, total_conversions),
        avg_ctr=float(row.avg_ctr),
        budget_usage_pct=budget_usage,
        monthly_budget=monthly_budget,
    )


@router.get("/daily", response_model=DailyMetricsResponse)
async def get_daily_metrics(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily time-series metrics."""
    client = await _get_client(current_user, db)
    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            DailyMetrics.date,
            func.sum(DailyMetrics.spend).label("spend"),
            func.sum(DailyMetrics.revenue).label("revenue"),
            func.sum(DailyMetrics.conversions).label("conversions"),
            func.sum(DailyMetrics.clicks).label("clicks"),
            func.sum(DailyMetrics.impressions).label("impressions"),
        ).where(
            DailyMetrics.client_id == client.id,
            DailyMetrics.date >= start_date,
        ).group_by(DailyMetrics.date).order_by(DailyMetrics.date)
    )

    data = []
    for row in result.all():
        spend = float(row.spend or 0)
        revenue = float(row.revenue or 0)
        conversions = int(row.conversions or 0)
        data.append(DailyMetricPoint(
            date=row.date,
            spend=spend,
            revenue=revenue,
            conversions=conversions,
            roas=safe_divide(revenue, spend),
            cpa=safe_divide(spend, conversions),
            clicks=int(row.clicks or 0),
            impressions=int(row.impressions or 0),
        ))

    return DailyMetricsResponse(data=data, period_days=days)


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full dashboard overview combining all data."""
    client = await _get_client(current_user, db)

    # Get summary
    summary = await get_metrics_summary(days=30, current_user=current_user, db=db)

    # Get daily metrics
    daily = await get_daily_metrics(days=30, current_user=current_user, db=db)

    # Top campaigns by ROAS
    start_date = date.today() - timedelta(days=30)
    top_result = await db.execute(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.platform,
            Campaign.status,
            func.sum(DailyMetrics.spend).label("spend"),
            func.sum(DailyMetrics.revenue).label("revenue"),
            func.sum(DailyMetrics.conversions).label("conversions"),
        ).join(
            DailyMetrics, DailyMetrics.campaign_id == Campaign.id
        ).where(
            Campaign.client_id == client.id,
            DailyMetrics.date >= start_date,
        ).group_by(Campaign.id).order_by(func.sum(DailyMetrics.revenue).desc()).limit(10)
    )

    top_campaigns = []
    for row in top_result.all():
        spend = float(row.spend or 0)
        revenue = float(row.revenue or 0)
        top_campaigns.append(TopCampaign(
            campaign_id=str(row.id),
            name=row.name,
            platform=row.platform,
            spend=spend,
            revenue=revenue,
            roas=safe_divide(revenue, spend),
            conversions=int(row.conversions or 0),
            status=row.status,
        ))

    # Recent optimization actions count
    actions_result = await db.execute(
        select(func.count(OptimizationLog.id)).where(
            OptimizationLog.client_id == client.id,
            OptimizationLog.created_at >= start_date,
        )
    )
    recent_actions = actions_result.scalar() or 0

    return DashboardOverview(
        summary=summary,
        daily_metrics=daily.data,
        top_campaigns=top_campaigns,
        automation_status=client.automation_status.value if hasattr(client.automation_status, 'value') else str(client.automation_status),
        recent_actions=recent_actions,
    )
