"""Client management API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.budget_settings import BudgetSettings
from app.schemas.client import ClientUpdate, ClientResponse, BudgetSettingsUpdate, BudgetSettingsResponse
from app.utils.security import get_current_user

router = APIRouter()


async def get_client_for_user(user: User, db: AsyncSession) -> Client:
    """Get the primary client for the current user."""
    result = await db.execute(
        select(Client).where(Client.user_id == user.id, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="No active client found")
    return client


@router.get("/me", response_model=ClientResponse)
async def get_my_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's client profile."""
    return await get_client_for_user(current_user, db)


@router.put("/me", response_model=ClientResponse)
async def update_my_client(
    data: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's client settings."""
    client = await get_client_for_user(current_user, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    # Sync budget settings if monthly_budget changed
    if "monthly_budget" in update_data:
        result = await db.execute(
            select(BudgetSettings).where(BudgetSettings.client_id == client.id)
        )
        budget = result.scalar_one_or_none()
        if budget:
            budget.monthly_cap = update_data["monthly_budget"]

    return client


@router.get("/me/budget", response_model=BudgetSettingsResponse)
async def get_budget_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get budget allocation settings."""
    client = await get_client_for_user(current_user, db)
    result = await db.execute(
        select(BudgetSettings).where(BudgetSettings.client_id == client.id)
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget settings not found")
    return budget


@router.put("/me/budget", response_model=BudgetSettingsResponse)
async def update_budget_settings(
    data: BudgetSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update budget allocation settings."""
    client = await get_client_for_user(current_user, db)
    result = await db.execute(
        select(BudgetSettings).where(BudgetSettings.client_id == client.id)
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget settings not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate allocation percentages sum to ~1.0
    pct_fields = ["prospecting_pct", "retargeting_pct", "testing_pct"]
    new_pcts = {f: update_data.get(f, getattr(budget, f)) for f in pct_fields}
    total = sum(new_pcts.values())
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Budget allocations must sum to 100% (got {total*100:.1f}%)",
        )

    for field, value in update_data.items():
        setattr(budget, field, value)

    return budget
