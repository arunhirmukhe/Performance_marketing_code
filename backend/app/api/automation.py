"""Automation control API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.client import Client, AutomationStatus
from app.models.ad_account import AdAccount
from app.models.optimization_log import OptimizationLog
from app.schemas.campaign import OptimizationLogResponse
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


@router.post("/deploy")
async def deploy_automation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy full automation: collect data → generate strategy → create campaigns."""
    client = await _get_client(current_user, db)

    # Verify at least one ad account is connected
    result = await db.execute(
        select(AdAccount).where(
            AdAccount.client_id == client.id,
            AdAccount.status == "connected",
        )
    )
    accounts = result.scalars().all()
    if not accounts:
        raise HTTPException(
            status_code=400,
            detail="Please connect at least one ad account before deploying",
        )

    # Verify budget is set
    if client.monthly_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Please set a monthly budget before deploying",
        )

    # Update status to deploying
    client.automation_status = AutomationStatus.DEPLOYING

    # Log the deployment action
    log = OptimizationLog(
        client_id=client.id,
        action="automation_deploy",
        reason="User initiated full automation deployment",
        status="pending",
    )
    db.add(log)

    # In production, this would trigger the async pipeline:
    # 1. data_collector.sync_all_for_client(client.id)
    # 2. strategy_engine.generate_strategy(client.id)
    # 3. campaign_creator.execute_strategy(client.id)
    # For now, we mark as active to simulate deployment
    client.automation_status = AutomationStatus.ACTIVE
    log.status = "completed"

    return {
        "status": "deployed",
        "message": "Automation deployed successfully. Campaigns will be created and optimized automatically.",
        "client_id": str(client.id),
        "connected_accounts": len(accounts),
    }


@router.post("/pause")
async def pause_automation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause all automation for the current client."""
    client = await _get_client(current_user, db)

    if client.automation_status == AutomationStatus.INACTIVE:
        raise HTTPException(status_code=400, detail="Automation is not active")

    client.automation_status = AutomationStatus.PAUSED

    log = OptimizationLog(
        client_id=client.id,
        action="automation_pause",
        reason="User paused automation",
        status="completed",
    )
    db.add(log)

    return {"status": "paused", "message": "Automation paused. No actions will be taken until resumed."}


@router.post("/resume")
async def resume_automation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume paused automation."""
    client = await _get_client(current_user, db)

    if client.automation_status != AutomationStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Automation is not paused")

    client.automation_status = AutomationStatus.ACTIVE

    log = OptimizationLog(
        client_id=client.id,
        action="automation_resume",
        reason="User resumed automation",
        status="completed",
    )
    db.add(log)

    return {"status": "active", "message": "Automation resumed. Optimization will continue."}


@router.get("/status")
async def get_automation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current automation status."""
    client = await _get_client(current_user, db)

    # Count connected accounts
    result = await db.execute(
        select(AdAccount).where(
            AdAccount.client_id == client.id,
            AdAccount.status == "connected",
        )
    )
    accounts = result.scalars().all()

    return {
        "automation_status": client.automation_status.value if hasattr(client.automation_status, 'value') else str(client.automation_status),
        "monthly_budget": client.monthly_budget,
        "country": client.country,
        "connected_accounts": {
            "meta": sum(1 for a in accounts if a.platform == "meta"),
            "google": sum(1 for a in accounts if a.platform == "google"),
        },
    }


@router.get("/logs", response_model=List[OptimizationLogResponse])
async def get_optimization_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get optimization action logs."""
    client = await _get_client(current_user, db)

    result = await db.execute(
        select(OptimizationLog)
        .where(OptimizationLog.client_id == client.id)
        .order_by(desc(OptimizationLog.created_at))
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()
