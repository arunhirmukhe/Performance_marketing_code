"""Meta Marketing API service - handles all Meta/Facebook Ads interactions."""

import httpx
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v18.0"


class MetaAdsService:
    """Client for Meta Marketing API operations."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None
    ):
        self.access_token = access_token
        self.app_id = app_id or settings.META_APP_ID
        self.app_secret = app_secret or settings.META_APP_SECRET

    async def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> dict:
        """Exchange OAuth authorization code for access token."""
        uri = redirect_uri or settings.META_REDIRECT_URI
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_URL}/oauth/access_token",
                params={
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "redirect_uri": uri,
                    "code": code,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Exchange short-lived token for long-lived token
            long_lived = await client.get(
                f"{META_GRAPH_URL}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "fb_exchange_token": data["access_token"],
                },
            )
            long_lived.raise_for_status()
            return long_lived.json()

    async def get_ad_accounts(self, access_token: str) -> list[dict]:
        """Get all ad accounts accessible to the user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_URL}/me/adaccounts",
                params={
                    "access_token": access_token,
                    "fields": "id,name,account_status,currency,timezone_name",
                },
            )
            response.raise_for_status()
            return response.json().get("data", [])

    async def fetch_campaign_insights(
        self, account_id: str, access_token: str, date_start: str, date_end: str
    ) -> list[dict]:
        """Fetch campaign-level insights from Meta Ads."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{META_GRAPH_URL}/act_{account_id}/insights",
                params={
                    "access_token": access_token,
                    "level": "campaign",
                    "fields": (
                        "campaign_id,campaign_name,spend,impressions,clicks,"
                        "ctr,cpc,cpm,actions,action_values,frequency,reach"
                    ),
                    "time_range": f'{{"since":"{date_start}","until":"{date_end}"}}',
                    "time_increment": 1,  # Daily breakdown
                },
            )
            response.raise_for_status()
            return response.json().get("data", [])

    async def create_campaign(
        self, account_id: str, access_token: str,
        name: str, objective: str = "OUTCOME_SALES",
        daily_budget: float = 0, status: str = "PAUSED",
    ) -> dict:
        """Create a new campaign on Meta."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_URL}/act_{account_id}/campaigns",
                params={"access_token": access_token},
                json={
                    "name": name,
                    "objective": objective,
                    "status": status,
                    "special_ad_categories": [],
                    "daily_budget": int(daily_budget * 100),  # Meta uses cents
                },
            )
            response.raise_for_status()
            return response.json()

    async def create_ad_set(
        self, account_id: str, access_token: str,
        campaign_id: str, name: str, daily_budget: float,
        targeting: dict, optimization_goal: str = "OFFSITE_CONVERSIONS",
        billing_event: str = "IMPRESSIONS", status: str = "PAUSED",
    ) -> dict:
        """Create an ad set within a campaign."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_URL}/act_{account_id}/adsets",
                params={"access_token": access_token},
                json={
                    "name": name,
                    "campaign_id": campaign_id,
                    "daily_budget": int(daily_budget * 100),
                    "targeting": targeting,
                    "optimization_goal": optimization_goal,
                    "billing_event": billing_event,
                    "status": status,
                    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                },
            )
            response.raise_for_status()
            return response.json()

    async def create_ad(
        self, account_id: str, access_token: str,
        ad_set_id: str, name: str, creative_id: str,
        status: str = "PAUSED",
    ) -> dict:
        """Create an ad within an ad set."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_URL}/act_{account_id}/ads",
                params={"access_token": access_token},
                json={
                    "name": name,
                    "adset_id": ad_set_id,
                    "creative": {"creative_id": creative_id},
                    "status": status,
                },
            )
            response.raise_for_status()
            return response.json()

    async def update_campaign_budget(
        self, campaign_id: str, access_token: str, daily_budget: float
    ) -> dict:
        """Update a campaign's daily budget."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_URL}/{campaign_id}",
                params={"access_token": access_token},
                json={"daily_budget": int(daily_budget * 100)},
            )
            response.raise_for_status()
            return response.json()

    async def update_campaign_status(
        self, campaign_id: str, access_token: str, status: str
    ) -> dict:
        """Pause or activate a campaign."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{META_GRAPH_URL}/{campaign_id}",
                params={"access_token": access_token},
                json={"status": status},  # ACTIVE or PAUSED
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_conversions(actions: list[dict]) -> int:
        """Extract purchase/conversion count from Meta actions array."""
        if not actions:
            return 0
        for action in actions:
            if action.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                return int(action.get("value", 0))
        return 0

    @staticmethod
    def parse_revenue(action_values: list[dict]) -> float:
        """Extract revenue from Meta action_values array."""
        if not action_values:
            return 0.0
        for av in action_values:
            if av.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                return float(av.get("value", 0))
        return 0.0
