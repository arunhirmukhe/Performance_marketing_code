"""Ad Account connection API routes - OAuth flows for Meta & Google."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from urllib.parse import urlencode

from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.ad_account import AdAccount
from app.schemas.ad_account import AdAccountResponse, OAuthURLResponse
from app.utils.security import get_current_user
from app.config import settings
from app.services.meta_ads import MetaAdsService
from app.services.google_ads import GoogleAdsService

router = APIRouter()


async def _get_client(user: User, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client).where(Client.user_id == user.id, Client.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="No active client found")
    return client


# ─── Meta Ads OAuth ──────────────────────────────────────────────

@router.get("/meta/connect", response_model=OAuthURLResponse)
async def meta_connect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate Meta OAuth authorization URL using client credentials."""
    client = await _get_client(current_user, db)
    
    app_id = client.meta_app_id or settings.META_APP_ID
    if not app_id:
        raise HTTPException(status_code=400, detail="Meta App ID not configured for this client")

    params = {
        "client_id": app_id,
        "redirect_uri": settings.META_REDIRECT_URI,
        "scope": "ads_management,ads_read,business_management",
        "response_type": "code",
        "state": str(current_user.id),
    }
    auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    return OAuthURLResponse(auth_url=auth_url)


@router.get("/meta/callback")
async def meta_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Meta OAuth callback - exchange code for tokens."""
    try:
        from uuid import UUID
        user_id = UUID(state)
        
        # Get user's client
        result = await db.execute(
            select(Client).where(Client.user_id == user_id, Client.is_active == True)
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Initialize service with client credentials
        meta_service = MetaAdsService(
            app_id=client.meta_app_id,
            app_secret=client.meta_app_secret
        )
        token_data = await meta_service.exchange_code(code)

        # Get ad accounts for this user
        accounts = await meta_service.get_ad_accounts(token_data["access_token"])

        # Store each ad account
        for acct in accounts:
            existing = await db.execute(
                select(AdAccount).where(
                    AdAccount.client_id == client.id,
                    AdAccount.platform == "meta",
                    AdAccount.account_id == acct["id"],
                )
            )
            ad_account = existing.scalar_one_or_none()
            if ad_account:
                ad_account.access_token = token_data["access_token"]
                ad_account.status = "connected"
            else:
                ad_account = AdAccount(
                    client_id=client.id,
                    platform="meta",
                    account_id=acct["id"],
                    account_name=acct.get("name", "Meta Ad Account"),
                    access_token=token_data["access_token"],
                )
                db.add(ad_account)

        # Redirect to frontend success page
        return RedirectResponse(url="http://localhost:3001/setup?meta=connected")

    except Exception as e:
        return RedirectResponse(url=f"http://localhost:3001/setup?meta=error&msg={str(e)}")


# ─── Google Ads OAuth ────────────────────────────────────────────

@router.get("/google/connect", response_model=OAuthURLResponse)
async def google_connect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate Google Ads OAuth authorization URL using client credentials."""
    client = await _get_client(current_user, db)

    client_id = client.google_client_id or settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=400, detail="Google Client ID not configured for this client")

    params = {
        "client_id": client_id,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "https://www.googleapis.com/auth/adwords https://www.googleapis.com/auth/analytics.readonly",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": str(current_user.id),
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return OAuthURLResponse(auth_url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    try:
        from uuid import UUID
        user_id = UUID(state)

        # Get user's client
        result = await db.execute(
            select(Client).where(Client.user_id == user_id, Client.is_active == True)
        )
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Initialize service with client credentials
        google_service = GoogleAdsService(
            client_id=client.google_client_id,
            client_secret=client.google_client_secret,
            developer_token=client.google_developer_token
        )
        token_data = await google_service.exchange_code(code)

        # Get accessible customer IDs
        customers = await google_service.get_accessible_customers(token_data["access_token"])

        for customer_id in customers:
            existing = await db.execute(
                select(AdAccount).where(
                    AdAccount.client_id == client.id,
                    AdAccount.platform == "google",
                    AdAccount.account_id == customer_id,
                )
            )
            ad_account = existing.scalar_one_or_none()
            if ad_account:
                ad_account.access_token = token_data["access_token"]
                ad_account.refresh_token = token_data.get("refresh_token")
                ad_account.status = "connected"
            else:
                ad_account = AdAccount(
                    client_id=client.id,
                    platform="google",
                    account_id=customer_id,
                    account_name=f"Google Ads {customer_id}",
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                )
                db.add(ad_account)

        return RedirectResponse(url="http://localhost:3001/setup?google=connected")

    except Exception as e:
        return RedirectResponse(url=f"http://localhost:3001/setup?google=error&msg={str(e)}")


# ─── List Connected Accounts ────────────────────────────────────

@router.get("", response_model=List[AdAccountResponse])
async def list_ad_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all connected ad accounts for the current user's client."""
    client = await _get_client(current_user, db)
    result = await db.execute(
        select(AdAccount).where(AdAccount.client_id == client.id)
    )
    return result.scalars().all()
