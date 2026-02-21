"""Campaign listing API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignResponse, CampaignListResponse
from app.utils.security import get_current_user

router = APIRouter()


async def _get_client(user: User, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client).where(Client.user_id == user.id, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="No active client found")
    return client


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List campaigns for the current client."""
    client = await _get_client(current_user, db)

    query = select(Campaign).where(Campaign.client_id == client.id)
    count_query = select(func.count(Campaign.id)).where(Campaign.client_id == client.id)

    if status:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)
    if platform:
        query = query.where(Campaign.platform == platform)
        count_query = count_query.where(Campaign.platform == platform)

    query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return CampaignListResponse(campaigns=campaigns, total=total)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single campaign by ID."""
    from uuid import UUID
    client = await _get_client(current_user, db)

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == UUID(campaign_id),
            Campaign.client_id == client.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
