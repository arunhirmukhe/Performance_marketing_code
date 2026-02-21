"""Campaign Creation Engine - automated campaign setup from strategy."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.client import Client
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.ad_set import AdSet
from app.models.optimization_log import OptimizationLog
from app.services.meta_ads import MetaAdsService
from app.services.google_ads import GoogleAdsService

logger = logging.getLogger(__name__)


class CampaignCreator:
    """Creates campaigns on Meta and Google based on strategy engine output."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def execute_strategy(self, client_id, strategy: dict):
        """Create all campaigns and ad sets based on strategy."""
        async with self.session_factory() as db:
            # Get client for credentials
            result = await db.execute(select(Client).where(Client.id == client_id))
            client_obj = result.scalar_one_or_none()
            if not client_obj:
                return

            # Get connected accounts
            result = await db.execute(
                select(AdAccount).where(
                    AdAccount.client_id == client_id,
                    AdAccount.status == "connected",
                )
            )
            accounts = result.scalars().all()

            meta_accounts = [a for a in accounts if a.platform == "meta"]
            google_accounts = [a for a in accounts if a.platform == "google"]

            campaign_structure = strategy.get("campaign_structure", {})

            for meta_acct in meta_accounts:
                await self._create_meta_campaigns(db, client_obj, meta_acct, campaign_structure)

            for google_acct in google_accounts:
                await self._create_google_campaigns(db, client_obj, google_acct, campaign_structure)

            await db.commit()

    async def _create_meta_campaigns(
        self, db: AsyncSession, client_obj: Client, account: AdAccount, structure: dict
    ):
        """Create Meta campaigns from strategy structure."""
        meta = MetaAdsService(
            app_id=client_obj.meta_app_id,
            app_secret=client_obj.meta_app_secret
        )

        for campaign_type, config in structure.items():
            daily_budget = config.get("daily_budget", 0)
            if daily_budget <= 0:
                continue

            try:
                # Create campaign on Meta
                name = f"FAGE_{campaign_type.title()}_{account.account_id[:8]}"
                meta_response = await meta.create_campaign(
                    account_id=account.account_id,
                    access_token=account.access_token,
                    name=name,
                    objective="OUTCOME_SALES",
                    daily_budget=daily_budget,
                    status="PAUSED",  # Start paused for safety
                )

                platform_campaign_id = meta_response.get("id")

                # Save campaign to DB
                campaign = Campaign(
                    client_id=client_id,
                    ad_account_id=account.id,
                    platform_campaign_id=platform_campaign_id,
                    name=name,
                    platform="meta",
                    objective="OUTCOME_SALES",
                    campaign_type=campaign_type,
                    status="paused",
                    daily_budget=daily_budget,
                )
                db.add(campaign)
                await db.flush()

                # Create ad sets
                for ad_set_config in config.get("ad_sets", []):
                    ad_set_budget = daily_budget * ad_set_config["budget_pct"]
                    ad_set_type = ad_set_config["type"]

                    targeting = self._get_meta_targeting(ad_set_type)

                    try:
                        adset_response = await meta.create_ad_set(
                            account_id=account.account_id,
                            access_token=account.access_token,
                            campaign_id=platform_campaign_id,
                            name=f"{name}_{ad_set_type}",
                            daily_budget=ad_set_budget,
                            targeting=targeting,
                            status="PAUSED",
                        )

                        ad_set = AdSet(
                            campaign_id=campaign.id,
                            platform_adset_id=adset_response.get("id"),
                            name=f"{name}_{ad_set_type}",
                            targeting_type=ad_set_type,
                            status="paused",
                            daily_budget=ad_set_budget,
                            targeting_spec=targeting,
                        )
                        db.add(ad_set)
                    except Exception as e:
                        logger.error(f"Failed to create ad set {ad_set_type}: {e}")

                # Log action
                log = OptimizationLog(
                    client_id=client_id,
                    campaign_id=campaign.id,
                    action="campaign_created",
                    reason=f"Strategy-driven {campaign_type} campaign",
                    entity_type="campaign",
                    entity_id=platform_campaign_id,
                    status="completed",
                )
                db.add(log)

            except Exception as e:
                logger.error(f"Failed to create Meta {campaign_type} campaign: {e}")
                log = OptimizationLog(
                    client_id=client_id,
                    action="campaign_creation_failed",
                    reason=str(e),
                    entity_type="campaign",
                    status="failed",
                    error_message=str(e),
                )
                db.add(log)

    async def _create_google_campaigns(
        self, db: AsyncSession, client_obj: Client, account: AdAccount, structure: dict
    ):
        """Create Google Ads campaigns from strategy structure."""
        google = GoogleAdsService(
            client_id=client_obj.google_client_id,
            client_secret=client_obj.google_client_secret,
            developer_token=client_obj.google_developer_token
        )

        # Create Shopping campaign for prospecting
        prospecting = structure.get("prospecting", {})
        budget = prospecting.get("daily_budget", 0)

        if budget > 0:
            try:
                name = f"FAGE_Shopping_{account.account_id[:8]}"
                google_response = await google.create_campaign(
                    customer_id=account.account_id,
                    access_token=account.access_token,
                    name=name,
                    channel_type="SHOPPING",
                    budget_amount_micros=int(budget * 1_000_000),
                    status="PAUSED",
                )

                campaign_resource = google_response.get("results", [{}])[0].get("resourceName", "")

                campaign = Campaign(
                    client_id=client_id,
                    ad_account_id=account.id,
                    platform_campaign_id=campaign_resource,
                    name=name,
                    platform="google",
                    objective="SHOPPING",
                    campaign_type="prospecting",
                    status="paused",
                    daily_budget=budget,
                )
                db.add(campaign)

                log = OptimizationLog(
                    client_id=client_id,
                    action="campaign_created",
                    reason="Strategy-driven Google Shopping campaign",
                    entity_type="campaign",
                    entity_id=campaign_resource,
                    status="completed",
                )
                db.add(log)

            except Exception as e:
                logger.error(f"Failed to create Google campaign: {e}")

        # Create Search campaign for retargeting/RLSA
        retargeting = structure.get("retargeting", {})
        retargeting_budget = retargeting.get("daily_budget", 0)

        if retargeting_budget > 0:
            try:
                name = f"FAGE_Search_{account.account_id[:8]}"
                await google.create_campaign(
                    customer_id=account.account_id,
                    access_token=account.access_token,
                    name=name,
                    channel_type="SEARCH",
                    budget_amount_micros=int(retargeting_budget * 1_000_000),
                    status="PAUSED",
                )
            except Exception as e:
                logger.error(f"Failed to create Google Search campaign: {e}")

    @staticmethod
    def _get_meta_targeting(ad_set_type: str) -> dict:
        """Get Meta targeting spec based on ad set type."""
        base_targeting = {
            "age_min": 18,
            "age_max": 65,
            "publisher_platforms": ["facebook", "instagram"],
        }

        if ad_set_type == "broad":
            return {**base_targeting}
        elif ad_set_type == "interest":
            return {
                **base_targeting,
                "flexible_spec": [{"interests": []}],  # Populated per client
            }
        elif ad_set_type == "lookalike":
            return {
                **base_targeting,
                "custom_audiences": [],  # Populated with lookalike audience ID
            }
        elif ad_set_type in ("website_visitors", "engaged_users", "cart_abandoners"):
            return {
                **base_targeting,
                "custom_audiences": [],  # Populated with retargeting audience ID
            }
        else:
            return base_targeting
