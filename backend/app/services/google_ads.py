"""Google Ads API service - handles all Google Ads interactions."""

import httpx
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

GOOGLE_ADS_API_URL = "https://googleads.googleapis.com/v15"
GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/token"


class GoogleAdsService:
    """Client for Google Ads API operations."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        developer_token: Optional[str] = None
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self.developer_token = developer_token or settings.GOOGLE_DEVELOPER_TOKEN

    async def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> dict:
        """Exchange OAuth authorization code for tokens."""
        uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_OAUTH_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_OAUTH_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_accessible_customers(self, access_token: str) -> list[str]:
        """Get all customer IDs accessible to the authenticated user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_ADS_API_URL}/customers:listAccessibleCustomers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": self.developer_token or "",
                },
            )
            response.raise_for_status()
            data = response.json()
            # Returns list like ["customers/1234567890"]
            return [c.split("/")[-1] for c in data.get("resourceNames", [])]

    async def fetch_campaign_performance(
        self, customer_id: str, access_token: str,
        date_start: str, date_end: str,
    ) -> list[dict]:
        """Fetch campaign performance data using Google Ads GAQL."""
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.conversions,
                metrics.conversions_value,
                segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
            ORDER BY segments.date DESC
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/googleAds:searchStream",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.GOOGLE_DEVELOPER_TOKEN or "",
                },
                json={"query": query},
            )
            response.raise_for_status()
            results = response.json()

            parsed = []
            for batch in results:
                for row in batch.get("results", []):
                    campaign = row.get("campaign", {})
                    metrics = row.get("metrics", {})
                    segments = row.get("segments", {})
                    parsed.append({
                        "campaign_id": campaign.get("id"),
                        "campaign_name": campaign.get("name"),
                        "status": campaign.get("status"),
                        "channel_type": campaign.get("advertisingChannelType"),
                        "date": segments.get("date"),
                        "spend": int(metrics.get("costMicros", 0)) / 1_000_000,
                        "impressions": int(metrics.get("impressions", 0)),
                        "clicks": int(metrics.get("clicks", 0)),
                        "ctr": float(metrics.get("ctr", 0)),
                        "cpc": int(metrics.get("averageCpc", 0)) / 1_000_000,
                        "conversions": int(float(metrics.get("conversions", 0))),
                        "revenue": float(metrics.get("conversionsValue", 0)),
                    })
            return parsed

    async def create_campaign(
        self, customer_id: str, access_token: str,
        name: str, channel_type: str = "SHOPPING",
        budget_amount_micros: int = 0, status: str = "PAUSED",
    ) -> dict:
        """Create a Google Ads campaign."""
        # Step 1: Create campaign budget
        async with httpx.AsyncClient() as client:
            budget_response = await client.post(
                f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/campaignBudgets:mutate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.GOOGLE_DEVELOPER_TOKEN or "",
                },
                json={
                    "operations": [{
                        "create": {
                            "name": f"{name} Budget",
                            "amountMicros": str(budget_amount_micros),
                            "deliveryMethod": "STANDARD",
                        }
                    }]
                },
            )
            budget_response.raise_for_status()
            budget_data = budget_response.json()
            budget_resource = budget_data["results"][0]["resourceName"]

            # Step 2: Create campaign
            campaign_response = await client.post(
                f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/campaigns:mutate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.GOOGLE_DEVELOPER_TOKEN or "",
                },
                json={
                    "operations": [{
                        "create": {
                            "name": name,
                            "advertisingChannelType": channel_type,
                            "status": status,
                            "campaignBudget": budget_resource,
                            "biddingStrategyType": "MAXIMIZE_CONVERSION_VALUE",
                        }
                    }]
                },
            )
            campaign_response.raise_for_status()
            return campaign_response.json()

    async def update_campaign_budget(
        self, customer_id: str, access_token: str,
        campaign_budget_resource: str, new_amount_micros: int,
    ) -> dict:
        """Update a campaign budget."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/campaignBudgets:mutate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.GOOGLE_DEVELOPER_TOKEN or "",
                },
                json={
                    "operations": [{
                        "update": {
                            "resourceName": campaign_budget_resource,
                            "amountMicros": str(new_amount_micros),
                        },
                        "updateMask": "amountMicros",
                    }]
                },
            )
            response.raise_for_status()
            return response.json()

    async def update_campaign_status(
        self, customer_id: str, access_token: str,
        campaign_resource: str, status: str,
    ) -> dict:
        """Pause or enable a campaign."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/campaigns:mutate",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.GOOGLE_DEVELOPER_TOKEN or "",
                },
                json={
                    "operations": [{
                        "update": {
                            "resourceName": campaign_resource,
                            "status": status,  # ENABLED or PAUSED
                        },
                        "updateMask": "status",
                    }]
                },
            )
            response.raise_for_status()
            return response.json()
