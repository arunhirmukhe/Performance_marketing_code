"""Budget Manager - enforces caps, detects anomalies, tracks spend."""

import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from app.models.client import Client, AutomationStatus
from app.models.daily_metrics import DailyMetrics
from app.models.budget_settings import BudgetSettings
from app.models.campaign import Campaign
from app.services.meta_ads import MetaAdsService
from app.services.google_ads import GoogleAdsService
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class BudgetManager:
    """Monitors and enforces budget safety across all clients."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.alert_service = AlertService()

    async def check_all_budgets(self):
        """Run budget safety checks for all active clients."""
        async with self.session_factory() as db:
            result = await db.execute(
                select(Client).where(
                    Client.automation_status == AutomationStatus.ACTIVE,
                    Client.is_active == True,
                )
            )
            clients = result.scalars().all()

        for client in clients:
            try:
                await self.check_client_budget(client.id)
            except Exception as e:
                logger.error(f"Budget check failed for client {client.id}: {e}")

    async def check_client_budget(self, client_id):
        """Run all budget safety checks for a client."""
        async with self.session_factory() as db:
            # Get budget settings
            result = await db.execute(
                select(BudgetSettings).where(BudgetSettings.client_id == client_id)
            )
            budget = result.scalar_one_or_none()
            if not budget or budget.monthly_cap <= 0:
                return

            # Calculate current month spend
            first_of_month = date.today().replace(day=1)
            spend_result = await db.execute(
                select(func.coalesce(func.sum(DailyMetrics.spend), 0)).where(
                    DailyMetrics.client_id == client_id,
                    DailyMetrics.date >= first_of_month,
                )
            )
            current_spend = float(spend_result.scalar())
            budget.current_month_spend = current_spend

            # Check 1: Monthly cap approaching
            usage_pct = current_spend / budget.monthly_cap
            if usage_pct >= budget.monthly_spend_alert_pct:
                await self.alert_service.send_alert(
                    title="⚠️ Budget Alert: Monthly Cap Approaching",
                    message=(
                        f"Client has spent ${current_spend:,.2f} of "
                        f"${budget.monthly_cap:,.2f} monthly budget "
                        f"({usage_pct*100:.1f}%)"
                    ),
                    level="warning",
                )

            # Check 2: Monthly cap exceeded → pause all campaigns
            if current_spend >= budget.monthly_cap:
                await self._pause_all_campaigns(db, client_id)
                await self.alert_service.send_alert(
                    title="🛑 Budget Cap Reached - Campaigns Paused",
                    message=(
                        f"Monthly budget of ${budget.monthly_cap:,.2f} exceeded. "
                        f"All campaigns have been paused."
                    ),
                    level="critical",
                )

            # Check 3: Abnormal daily spend detection
            await self._check_abnormal_spend(db, client_id, budget)

            await db.commit()

    async def _check_abnormal_spend(
        self, db: AsyncSession, client_id, budget: BudgetSettings
    ):
        """Detect abnormally high daily spend."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Yesterday's spend
        result = await db.execute(
            select(func.coalesce(func.sum(DailyMetrics.spend), 0)).where(
                DailyMetrics.client_id == client_id,
                DailyMetrics.date == yesterday,
            )
        )
        yesterday_spend = float(result.scalar())

        # Average daily spend over last 7 days
        week_ago = today - timedelta(days=7)
        avg_result = await db.execute(
            select(func.coalesce(func.avg(DailyMetrics.spend), 0)).where(
                DailyMetrics.client_id == client_id,
                DailyMetrics.date >= week_ago,
                DailyMetrics.date < yesterday,
            )
        )
        avg_daily = float(avg_result.scalar())

        # Alert if yesterday's spend is > 2x average
        if avg_daily > 0 and yesterday_spend > avg_daily * 2:
            await self.alert_service.send_alert(
                title="⚠️ Abnormal Spend Detected",
                message=(
                    f"Yesterday's spend (${yesterday_spend:,.2f}) was "
                    f"{yesterday_spend/avg_daily:.1f}x the 7-day average "
                    f"(${avg_daily:,.2f})"
                ),
                level="warning",
            )

    async def _pause_all_campaigns(self, db: AsyncSession, client_id):
        """Pause all active campaigns for a client."""
        # Get client for credentials
        result = await db.execute(select(Client).where(Client.id == client_id))
        client_obj = result.scalar_one_or_none()
        if not client_obj:
            return

        result = await db.execute(
            select(Campaign).where(
                Campaign.client_id == client_id,
                Campaign.status == "active",
            )
        )
        campaigns = result.scalars().all()

        for campaign in campaigns:
            try:
                # Pause on platform
                result = await db.execute(
                    select(AdAccount).where(AdAccount.id == campaign.ad_account_id)
                )
                account = result.scalar_one_or_none()
                
                if account:
                    if campaign.platform == "meta":
                        meta = MetaAdsService(
                            app_id=client_obj.meta_app_id,
                            app_secret=client_obj.meta_app_secret
                        )
                        await meta.update_campaign_status(
                            campaign.platform_campaign_id, account.access_token, "PAUSED"
                        )
                    elif campaign.platform == "google":
                        google = GoogleAdsService(
                            client_id=client_obj.google_client_id,
                            client_secret=client_obj.google_client_secret,
                            developer_token=client_obj.google_developer_token
                        )
                        await google.update_campaign_status(
                            account.account_id, account.access_token,
                            campaign.platform_campaign_id, "PAUSED"
                        )
                
                campaign.status = "paused"
                logger.warning(f"Paused campaign {campaign.name} on {campaign.platform} due to budget cap")
            except Exception as e:
                logger.error(f"Failed to pause campaign {campaign.name} on platform: {e}")

        # Update client status
        client_obj.automation_status = AutomationStatus.PAUSED
