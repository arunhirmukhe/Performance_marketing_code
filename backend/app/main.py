"""FAGE - Fibonce Autonomous Growth Engine: FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, clients, campaigns, dashboard, ad_accounts, automation
from app.tasks.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(clients.router, prefix=f"{settings.API_PREFIX}/clients", tags=["Clients"])
app.include_router(ad_accounts.router, prefix=f"{settings.API_PREFIX}/ad-accounts", tags=["Ad Accounts"])
app.include_router(campaigns.router, prefix=f"{settings.API_PREFIX}/campaigns", tags=["Campaigns"])
app.include_router(dashboard.router, prefix=f"{settings.API_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(automation.router, prefix=f"{settings.API_PREFIX}/automation", tags=["Automation"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}
