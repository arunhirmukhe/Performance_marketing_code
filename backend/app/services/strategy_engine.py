"""Strategy Engine - Rule-based campaign strategy generation."""

import logging
from datetime import date, timedelta
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.client import Client
from app.models.daily_metrics import DailyMetrics
from app.models.budget_settings import BudgetSettings
from app.config import settings

logger = logging.getLogger(__name__)


class StrategyEngine:
    """
    Analyzes historical performance data and generates campaign strategy
    including budget allocation, targeting recommendations, and creative flags.
    """

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def generate_strategy(self, client_id) -> dict:
        """Generate a full campaign strategy for a client."""
        async with self.session_factory() as db:
            # Load last 30 days of metrics
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=29)

            result = await db.execute(
                select(DailyMetrics).where(
                    DailyMetrics.client_id == client_id,
                    DailyMetrics.date >= start_date,
                    DailyMetrics.date <= end_date,
                )
            )
            rows = result.scalars().all()

            if not rows:
                return self._default_strategy(client_id)

            # Convert to DataFrame for analysis
            df = pd.DataFrame([{
                "date": r.date,
                "campaign_id": str(r.campaign_id) if r.campaign_id else None,
                "platform": r.platform,
                "spend": r.spend,
                "impressions": r.impressions,
                "clicks": r.clicks,
                "ctr": r.ctr,
                "conversions": r.conversions,
                "revenue": r.revenue,
                "roas": r.roas,
                "cpa": r.cpa,
                "frequency": r.frequency or 0,
            } for r in rows])

            # Get budget settings
            budget_result = await db.execute(
                select(BudgetSettings).where(BudgetSettings.client_id == client_id)
            )
            budget = budget_result.scalar_one_or_none()

            return self._analyze_and_recommend(df, budget)

    def _analyze_and_recommend(self, df: pd.DataFrame, budget: BudgetSettings) -> dict:
        """Core analysis logic."""
        total_spend = df["spend"].sum()
        total_revenue = df["revenue"].sum()
        overall_roas = total_revenue / total_spend if total_spend > 0 else 0
        avg_ctr = df["ctr"].mean()
        avg_cpa = df["cpa"].mean()
        avg_frequency = df["frequency"].mean()

        # ─── Budget Allocation Recommendations ───────────────────
        prospecting_pct = budget.prospecting_pct if budget else 0.50
        retargeting_pct = budget.retargeting_pct if budget else 0.35
        testing_pct = budget.testing_pct if budget else 0.15

        # Rule: If retargeting ROAS > 4, increase retargeting allocation
        # (Approximate by looking at high-ROAS campaigns)
        high_roas_campaigns = df[df["roas"] > 4.0]
        if len(high_roas_campaigns) > len(df) * 0.3:
            retargeting_pct = min(retargeting_pct + 0.05, 0.50)
            prospecting_pct = max(prospecting_pct - 0.05, 0.30)

        # Rule: If ROAS below threshold, reduce testing and increase retargeting
        if overall_roas < settings.DEFAULT_ROAS_THRESHOLD:
            testing_pct = max(testing_pct - 0.05, 0.05)
            retargeting_pct = min(retargeting_pct + 0.05, 0.55)

        # ─── Creative Analysis ───────────────────────────────────
        creative_flags = []

        # Rule: CTR < 0.8% → weak creative
        if avg_ctr < settings.DEFAULT_CTR_THRESHOLD:
            creative_flags.append({
                "flag": "weak_ctr",
                "message": f"Average CTR ({avg_ctr*100:.2f}%) is below threshold ({settings.DEFAULT_CTR_THRESHOLD*100:.1f}%)",
                "action": "Refresh ad creatives with stronger hooks",
            })

        # Rule: Frequency > 3 → creative fatigue
        if avg_frequency > settings.DEFAULT_FREQUENCY_THRESHOLD:
            creative_flags.append({
                "flag": "high_frequency",
                "message": f"Average frequency ({avg_frequency:.1f}) exceeds threshold ({settings.DEFAULT_FREQUENCY_THRESHOLD})",
                "action": "Rotate creatives and expand audiences",
            })

        # ─── Campaign Structure Recommendation ───────────────────
        monthly_budget = budget.monthly_cap if budget else 0
        daily_budget = monthly_budget / 30 if monthly_budget > 0 else 0

        campaign_structure = {
            "prospecting": {
                "daily_budget": daily_budget * prospecting_pct,
                "ad_sets": [
                    {"type": "broad", "budget_pct": 0.40},
                    {"type": "interest", "budget_pct": 0.35},
                    {"type": "lookalike", "budget_pct": 0.25},
                ],
            },
            "retargeting": {
                "daily_budget": daily_budget * retargeting_pct,
                "ad_sets": [
                    {"type": "website_visitors", "budget_pct": 0.50},
                    {"type": "engaged_users", "budget_pct": 0.30},
                    {"type": "cart_abandoners", "budget_pct": 0.20},
                ],
            },
            "testing": {
                "daily_budget": daily_budget * testing_pct,
                "ad_sets": [
                    {"type": "creative_test", "budget_pct": 0.60},
                    {"type": "audience_test", "budget_pct": 0.40},
                ],
            },
        }

        return {
            "client_id": str(budget.client_id) if budget else None,
            "analysis_period_days": 30,
            "overall_metrics": {
                "total_spend": round(total_spend, 2),
                "total_revenue": round(total_revenue, 2),
                "roas": round(overall_roas, 2),
                "avg_ctr": round(avg_ctr * 100, 2),
                "avg_cpa": round(avg_cpa, 2),
            },
            "budget_allocation": {
                "prospecting_pct": round(prospecting_pct, 2),
                "retargeting_pct": round(retargeting_pct, 2),
                "testing_pct": round(testing_pct, 2),
            },
            "campaign_structure": campaign_structure,
            "creative_flags": creative_flags,
            "monthly_budget": monthly_budget,
            "daily_budget": round(daily_budget, 2),
        }

    def _default_strategy(self, client_id) -> dict:
        """Return default strategy when no historical data exists."""
        return {
            "client_id": str(client_id),
            "analysis_period_days": 0,
            "overall_metrics": None,
            "budget_allocation": {
                "prospecting_pct": 0.50,
                "retargeting_pct": 0.35,
                "testing_pct": 0.15,
            },
            "campaign_structure": {
                "prospecting": {
                    "daily_budget": 0,
                    "ad_sets": [
                        {"type": "broad", "budget_pct": 0.40},
                        {"type": "interest", "budget_pct": 0.35},
                        {"type": "lookalike", "budget_pct": 0.25},
                    ],
                },
                "retargeting": {
                    "daily_budget": 0,
                    "ad_sets": [
                        {"type": "website_visitors", "budget_pct": 0.50},
                        {"type": "engaged_users", "budget_pct": 0.30},
                        {"type": "cart_abandoners", "budget_pct": 0.20},
                    ],
                },
                "testing": {
                    "daily_budget": 0,
                    "ad_sets": [
                        {"type": "creative_test", "budget_pct": 0.60},
                        {"type": "audience_test", "budget_pct": 0.40},
                    ],
                },
            },
            "creative_flags": [],
            "monthly_budget": 0,
            "daily_budget": 0,
        }
