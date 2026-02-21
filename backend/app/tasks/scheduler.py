"""APScheduler setup - manages all background automation tasks."""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import AsyncSessionLocal
from app.services.data_collector import DataCollector
from app.services.optimizer import Optimizer
from app.services.strategy_engine import StrategyEngine
from app.services.budget_manager import BudgetManager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def job_sync_data():
    """Daily data sync from all ad platforms."""
    logger.info("Starting scheduled data sync...")
    collector = DataCollector(AsyncSessionLocal)
    await collector.sync_all_clients()
    logger.info("Data sync completed.")


async def job_daily_optimization():
    """Daily campaign optimization."""
    logger.info("Starting daily optimization...")
    optimizer = Optimizer(AsyncSessionLocal)
    await optimizer.run_daily_optimization()
    logger.info("Daily optimization completed.")


async def job_weekly_strategy():
    """Weekly strategy recalculation."""
    logger.info("Starting weekly strategy recalculation...")
    # In full implementation, this would iterate clients and
    # regenerate strategies, adjusting budget allocations.
    from sqlalchemy import select
    from app.models.client import Client, AutomationStatus

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Client).where(
                Client.automation_status == AutomationStatus.ACTIVE,
                Client.is_active == True,
            )
        )
        clients = result.scalars().all()

    engine = StrategyEngine(AsyncSessionLocal)
    for client in clients:
        try:
            strategy = await engine.generate_strategy(client.id)
            logger.info(f"Strategy updated for client {client.id}: ROAS target = {strategy.get('overall_metrics', {})}")
        except Exception as e:
            logger.error(f"Strategy generation failed for client {client.id}: {e}")

    logger.info("Weekly strategy recalculation completed.")


async def job_budget_check():
    """Check budget safety for all clients."""
    logger.info("Running budget safety check...")
    manager = BudgetManager(AsyncSessionLocal)
    await manager.check_all_budgets()
    logger.info("Budget safety check completed.")


def start_scheduler():
    """Start the APScheduler with all scheduled jobs."""
    # Daily data sync at 2:00 AM
    scheduler.add_job(
        job_sync_data,
        CronTrigger(hour=2, minute=0),
        id="daily_data_sync",
        name="Daily Data Sync",
        replace_existing=True,
    )

    # Daily optimization at 6:00 AM
    scheduler.add_job(
        job_daily_optimization,
        CronTrigger(hour=6, minute=0),
        id="daily_optimization",
        name="Daily Optimization",
        replace_existing=True,
    )

    # Weekly strategy on Mondays at 3:00 AM
    scheduler.add_job(
        job_weekly_strategy,
        CronTrigger(day_of_week="mon", hour=3, minute=0),
        id="weekly_strategy",
        name="Weekly Strategy Recalculation",
        replace_existing=True,
    )

    # Budget safety check every 4 hours
    scheduler.add_job(
        job_budget_check,
        IntervalTrigger(hours=4),
        id="budget_check",
        name="Budget Safety Check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with 4 jobs: data_sync, optimization, strategy, budget_check")


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")
