"""Optimization Engine - daily automated campaign optimization."""

import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from app.models.client import Client, AutomationStatus
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.daily_metrics import DailyMetrics
from app.models.optimization_log import OptimizationLog
from app.services.meta_ads import MetaAdsService
from app.services.google_ads import GoogleAdsService
from app.config import settings

logger = logging.getLogger(__name__)


class Optimizer:
    """
    Runs daily optimization rules on all active campaigns.
    Rules:
    - ROAS > 3 for 3 consecutive days → increase budget 20%
    - CPA too high → decrease budget 15%
    - High spend + 0 conversions → pause ad
    - Top performer → duplicate to scaling campaign
    """

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def run_daily_optimization(self):
        """Run optimization for all active clients."""
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
                await self.optimize_client(client.id)
                logger.info(f"Optimization complete for client {client.id}")
            except Exception as e:
                logger.error(f"Optimization failed for client {client.id}: {e}")

    async def optimize_client(self, client_id):
        """Run all optimization rules for a single client."""
        async with self.session_factory() as db:
            # Get client for credentials
            result = await db.execute(select(Client).where(Client.id == client_id))
            client_obj = result.scalar_one_or_none()
            if not client_obj:
                return

            # Get all active campaigns
            result = await db.execute(
                select(Campaign).where(
                    Campaign.client_id == client_id,
                    Campaign.status == "active",
                )
            )
            campaigns = result.scalars().all()

            for campaign in campaigns:
                await self._optimize_campaign(db, client_obj, campaign)

            await db.commit()

    async def _optimize_campaign(self, db: AsyncSession, client_obj: Client, campaign: Campaign):
        """Apply optimization rules to a single campaign."""
        today = date.today()

        # Get last 3 days of metrics
        result = await db.execute(
            select(DailyMetrics).where(
                DailyMetrics.campaign_id == campaign.id,
                DailyMetrics.date >= today - timedelta(days=3),
            ).order_by(DailyMetrics.date.desc())
        )
        recent_metrics = result.scalars().all()

        if not recent_metrics:
            return

        # Get ad account for API calls
        result = await db.execute(
            select(AdAccount).where(AdAccount.id == campaign.ad_account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return

        # Rule 1: ROAS > 3 for 3 consecutive days → increase budget 20%
        await self._rule_scale_winners(db, client_obj, campaign, recent_metrics, account)

        # Rule 2: CPA too high → decrease budget 15%
        await self._rule_reduce_high_cpa(db, client_obj, campaign, recent_metrics, account)

        # Rule 3: High spend + 0 conversions → pause
        await self._rule_pause_no_conversions(db, client_obj, campaign, recent_metrics, account)

    async def _rule_scale_winners(
        self, db: AsyncSession, client_obj: Client, campaign: Campaign,
        metrics: list[DailyMetrics], account: AdAccount,
    ):
        """Scale budget for consistently high-performing campaigns."""
        if len(metrics) < 3:
            return

        # Check if ROAS > threshold for all 3 recent days
        all_high_roas = all(m.roas > settings.DEFAULT_ROAS_THRESHOLD for m in metrics[:3])

        if not all_high_roas:
            return

        new_budget = campaign.daily_budget * (1 + settings.BUDGET_INCREASE_PCT)
        old_budget = campaign.daily_budget

        try:
            if campaign.platform == "meta":
                meta = MetaAdsService(
                    app_id=client_obj.meta_app_id,
                    app_secret=client_obj.meta_app_secret
                )
                await meta.update_campaign_budget(
                    campaign.platform_campaign_id, account.access_token, new_budget
                )
            elif campaign.platform == "google":
                google = GoogleAdsService(
                    client_id=client_obj.google_client_id,
                    client_secret=client_obj.google_client_secret,
                    developer_token=client_obj.google_developer_token
                )
                await google.update_campaign_budget(
                    account.account_id, account.access_token,
                    campaign.platform_campaign_id, int(new_budget * 1_000_000)
                )

            campaign.daily_budget = new_budget

            log = OptimizationLog(
                client_id=client_obj.id,
                campaign_id=campaign.id,
                action="budget_increase",
                reason=f"ROAS > {settings.DEFAULT_ROAS_THRESHOLD} for 3 consecutive days",
                entity_type="campaign",
                entity_id=campaign.platform_campaign_id,
                old_value=f"${old_budget:.2f}",
                new_value=f"${new_budget:.2f}",
                status="completed",
            )
            db.add(log)
            logger.info(f"Scaled campaign {campaign.name}: ${old_budget:.2f} → ${new_budget:.2f}")

        except Exception as e:
            logger.error(f"Failed to scale campaign {campaign.name}: {e}")
            log = OptimizationLog(
                client_id=client_obj.id,
                campaign_id=campaign.id,
                action="budget_increase",
                reason=f"ROAS > {settings.DEFAULT_ROAS_THRESHOLD} for 3 days",
                status="failed",
                error_message=str(e),
            )
            db.add(log)

    async def _rule_reduce_high_cpa(
        self, db: AsyncSession, client_obj: Client, campaign: Campaign,
        metrics: list[DailyMetrics], account: AdAccount,
    ):
        """Reduce budget when CPA is too high."""
        if not metrics:
            return

        avg_cpa = sum(m.cpa for m in metrics) / len(metrics)

        if avg_cpa <= settings.DEFAULT_CPA_THRESHOLD or avg_cpa == 0:
            return

        new_budget = campaign.daily_budget * (1 - settings.BUDGET_DECREASE_PCT)
        old_budget = campaign.daily_budget

        # Minimum budget floor
        new_budget = max(new_budget, 5.0)

        try:
            if campaign.platform == "meta":
                meta = MetaAdsService(
                    app_id=client_obj.meta_app_id,
                    app_secret=client_obj.meta_app_secret
                )
                await meta.update_campaign_budget(
                    campaign.platform_campaign_id, account.access_token, new_budget
                )
            elif campaign.platform == "google":
                google = GoogleAdsService(
                    client_id=client_obj.google_client_id,
                    client_secret=client_obj.google_client_secret,
                    developer_token=client_obj.google_developer_token
                )
                await google.update_campaign_budget(
                    account.account_id, account.access_token,
                    campaign.platform_campaign_id, int(new_budget * 1_000_000)
                )

            campaign.daily_budget = new_budget

            log = OptimizationLog(
                client_id=client_obj.id,
                campaign_id=campaign.id,
                action="budget_decrease",
                reason=f"CPA (${avg_cpa:.2f}) exceeds threshold (${settings.DEFAULT_CPA_THRESHOLD:.2f})",
                entity_type="campaign",
                entity_id=campaign.platform_campaign_id,
                old_value=f"${old_budget:.2f}",
                new_value=f"${new_budget:.2f}",
                status="completed",
            )
            db.add(log)

        except Exception as e:
            logger.error(f"Failed to reduce budget for {campaign.name}: {e}")

    async def _rule_pause_no_conversions(
        self, db: AsyncSession, client_obj: Client, campaign: Campaign,
        metrics: list[DailyMetrics], account: AdAccount,
    ):
        """Pause campaigns with spend but zero conversions."""
        if not metrics:
            return

        total_spend = sum(m.spend for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)

        # Only trigger if spent more than $50 with 0 conversions
        if total_conversions > 0 or total_spend < 50:
            return

        try:
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

            log = OptimizationLog(
                client_id=client_obj.id,
                campaign_id=campaign.id,
                action="campaign_paused",
                reason=f"Spent ${total_spend:.2f} with 0 conversions in last {len(metrics)} days",
                entity_type="campaign",
                entity_id=campaign.platform_campaign_id,
                old_value="active",
                new_value="paused",
                status="completed",
            )
            db.add(log)
            logger.info(f"Paused campaign {campaign.name} - no conversions")

        except Exception as e:
            logger.error(f"Failed to pause campaign {campaign.name}: {e}")
