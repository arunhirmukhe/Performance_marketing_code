"""Google Analytics 4 data service."""

import httpx
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

GA4_API_URL = "https://analyticsdata.googleapis.com/v1beta"


class GA4Service:
    """Client for Google Analytics 4 Data API."""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token

    async def fetch_metrics(
        self, property_id: str, access_token: str,
        date_start: str, date_end: str,
    ) -> list[dict]:
        """Fetch daily GA4 metrics: sessions, revenue, conversions."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GA4_API_URL}/properties/{property_id}:runReport",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "dateRanges": [{"startDate": date_start, "endDate": date_end}],
                    "dimensions": [{"name": "date"}],
                    "metrics": [
                        {"name": "sessions"},
                        {"name": "totalRevenue"},
                        {"name": "conversions"},
                        {"name": "bounceRate"},
                        {"name": "averageSessionDuration"},
                    ],
                    "orderBys": [{"dimension": {"dimensionName": "date"}}],
                },
            )
            response.raise_for_status()
            data = response.json()

            parsed = []
            for row in data.get("rows", []):
                dims = row.get("dimensionValues", [])
                mets = row.get("metricValues", [])
                parsed.append({
                    "date": dims[0]["value"] if dims else None,
                    "sessions": int(mets[0]["value"]) if len(mets) > 0 else 0,
                    "revenue": float(mets[1]["value"]) if len(mets) > 1 else 0.0,
                    "conversions": int(float(mets[2]["value"])) if len(mets) > 2 else 0,
                    "bounce_rate": float(mets[3]["value"]) if len(mets) > 3 else 0.0,
                    "avg_session_duration": float(mets[4]["value"]) if len(mets) > 4 else 0.0,
                })
            return parsed
