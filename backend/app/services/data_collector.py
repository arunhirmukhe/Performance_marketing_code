"""Data Collection Service - scheduled data sync from ad platforms."""

import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.client import Client, AutomationStatus
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.daily_metrics import DailyMetrics
from app.services.meta_ads import MetaAdsService
from app.services.google_ads import GoogleAdsService
from app.services.ga4 import GA4Service
from app.utils.helpers import safe_divide, calculate_roas, calculate_cpa, calculate_ctr

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects and stores performance data from all connected ad platforms."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def sync_all_clients(self):
        """Sync data for all active clients. Called by scheduler."""
        async with self.session_factory() as db:
            result = await db.execute(
                select(Client).where(
                    Client.is_active == True,
                    Client.automation_status.in_([
                        AutomationStatus.ACTIVE, AutomationStatus.DEPLOYING
                    ]),
                )
            )
            clients = result.scalars().all()

        for client in clients:
            try:
                await self.sync_client(client.id)
                logger.info(f"Data sync completed for client {client.id}")
            except Exception as e:
                logger.error(f"Data sync failed for client {client.id}: {e}")

    async def sync_client(self, client_id):
        """Sync all data for a single client."""
        async with self.session_factory() as db:
            # Get client for credentials
            result = await db.execute(select(Client).where(Client.id == client_id))
            client_obj = result.scalar_one_or_none()
            if not client_obj:
                return

            # Get all connected accounts
            result = await db.execute(
                select(AdAccount).where(
                    AdAccount.client_id == client_id,
                    AdAccount.status == "connected",
                )
            )
            accounts = result.scalars().all()

            for account in accounts:
                try:
                    if account.platform == "meta":
                        await self._sync_meta(db, client_obj, account)
                    elif account.platform == "google":
                        await self._sync_google(db, client_obj, account)
                        # Also sync GA4 if property ID is set
                        if client_obj.ga4_property_id:
                            await self._sync_ga4(db, client_obj, account)
                except Exception as e:
                    logger.error(f"Failed to sync {account.platform} account {account.account_id}: {e}")

            await db.commit()

    async def _sync_ga4(self, db: AsyncSession, client_obj: Client, account: AdAccount):
        """Sync GA4 data if property ID is present."""
        ga4 = GA4Service()
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=6)

        try:
            metrics = await ga4.fetch_metrics(
                property_id=client_obj.ga4_property_id,
                access_token=account.access_token,
                date_start=start_date.isoformat(),
                date_end=end_date.isoformat(),
            )

            for row in metrics:
                # GA4 metrics are stored per client/platform, not campaign (usually)
                # But for now, we can store them in a special "organic" or "total" campaign record
                # or just use them for verification. 
                # FAGE currently stores DailyMetrics per campaign.
                # We'll skip detailed GA4 storage for now until the schema supports it better,
                # but the infrastructure is ready.
                logger.info(f"Fetched GA4 metrics for client {client_obj.id}: {row}")
        except Exception as e:
            logger.error(f"GA4 sync failed for client {client_obj.id}: {e}")

    async def _sync_meta(self, db: AsyncSession, client_obj: Client, account: AdAccount):
        """Sync Meta Ads data for the last 7 days."""
        meta = MetaAdsService(
            app_id=client_obj.meta_app_id,
            app_secret=client_obj.meta_app_secret
        )
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=6)

        insights = await meta.fetch_campaign_insights(
            account_id=account.account_id,
            access_token=account.access_token,
            date_start=start_date.isoformat(),
            date_end=end_date.isoformat(),
        )

        for row in insights:
            campaign_id = row.get("campaign_id")
            row_date = row.get("date_start", str(end_date))
            spend = float(row.get("spend", 0))
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            conversions = meta.parse_conversions(row.get("actions", []))
            revenue = meta.parse_revenue(row.get("action_values", []))

            # Find or create campaign record
            campaign = await self._ensure_campaign(
                db, client_obj.id, account.id, campaign_id,
                row.get("campaign_name", "Unknown"), "meta"
            )

            # Upsert daily metrics
            await self._upsert_metrics(
                db, client_obj.id, campaign.id, "meta",
                date.fromisoformat(row_date[:10]),
                spend=spend, impressions=impressions, clicks=clicks,
                conversions=conversions, revenue=revenue,
                frequency=float(row.get("frequency", 0)),
                reach=int(row.get("reach", 0)),
            )

    async def _sync_google(self, db: AsyncSession, client_obj: Client, account: AdAccount):
        """Sync Google Ads data for the last 7 days."""
        google = GoogleAdsService(
            client_id=client_obj.google_client_id,
            client_secret=client_obj.google_client_secret,
            developer_token=client_obj.google_developer_token
        )
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=6)

        performance = await google.fetch_campaign_performance(
            customer_id=account.account_id,
            access_token=account.access_token,
            date_start=start_date.isoformat(),
            date_end=end_date.isoformat(),
        )

        for row in performance:
            campaign = await self._ensure_campaign(
                db, client_obj.id, account.id,
                str(row["campaign_id"]), row["campaign_name"], "google"
            )
            await self._upsert_metrics(
                db, client_obj.id, campaign.id, "google",
                date.fromisoformat(row["date"]),
                spend=row["spend"], impressions=row["impressions"],
                clicks=row["clicks"], conversions=row["conversions"],
                revenue=row["revenue"],
            )

    async def _ensure_campaign(
        self, db: AsyncSession, client_id, ad_account_id,
        platform_campaign_id: str, name: str, platform: str,
    ) -> Campaign:
        """Get or create a campaign reference in the DB."""
        result = await db.execute(
            select(Campaign).where(
                Campaign.client_id == client_id,
                Campaign.platform_campaign_id == platform_campaign_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            campaign = Campaign(
                client_id=client_id,
                ad_account_id=ad_account_id,
                platform_campaign_id=platform_campaign_id,
                name=name,
                platform=platform,
                status="active",
            )
            db.add(campaign)
            await db.flush()
        return campaign

    async def _upsert_metrics(
        self, db: AsyncSession, client_id, campaign_id,
        platform: str, metric_date: date, **kwargs,
    ):
        """Insert or update daily metrics."""
        spend = kwargs.get("spend", 0)
        impressions = kwargs.get("impressions", 0)
        clicks = kwargs.get("clicks", 0)
        conversions = kwargs.get("conversions", 0)
        revenue = kwargs.get("revenue", 0)

        result = await db.execute(
            select(DailyMetrics).where(
                DailyMetrics.client_id == client_id,
                DailyMetrics.campaign_id == campaign_id,
                DailyMetrics.platform == platform,
                DailyMetrics.date == metric_date,
            )
        )
        metrics = result.scalar_one_or_none()

        if metrics:
            metrics.spend = spend
            metrics.impressions = impressions
            metrics.clicks = clicks
            metrics.conversions = conversions
            metrics.revenue = revenue
            metrics.ctr = calculate_ctr(clicks, impressions)
            metrics.cpc = safe_divide(spend, clicks)
            metrics.cpm = safe_divide(spend * 1000, impressions)
            metrics.roas = calculate_roas(revenue, spend)
            metrics.cpa = calculate_cpa(spend, conversions)
            metrics.frequency = kwargs.get("frequency", 0)
            metrics.reach = kwargs.get("reach", 0)
        else:
            metrics = DailyMetrics(
                client_id=client_id,
                campaign_id=campaign_id,
                platform=platform,
                date=metric_date,
                spend=spend,
                impressions=impressions,
                clicks=clicks,
                ctr=calculate_ctr(clicks, impressions),
                cpc=safe_divide(spend, clicks),
                cpm=safe_divide(spend * 1000, impressions),
                conversions=conversions,
                revenue=revenue,
                roas=calculate_roas(revenue, spend),
                cpa=calculate_cpa(spend, conversions),
                frequency=kwargs.get("frequency", 0),
                reach=kwargs.get("reach", 0),
            )
            db.add(metrics)
