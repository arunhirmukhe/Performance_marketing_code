"""Webhook handlers for external notifications."""

from fastapi import APIRouter, Request, HTTPException
import json

router = APIRouter()


@router.post("/meta")
async def meta_webhook(request: Request):
    """Handle Meta webhook notifications (ad status changes, etc.)."""
    try:
        body = await request.json()
        # Process webhook payload
        # In production: validate signature, process events
        return {"status": "received"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meta")
async def meta_webhook_verify(request: Request):
    """Meta webhook verification endpoint."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token:
        # In production: verify token matches your configured verify token
        return int(challenge) if challenge else ""
    raise HTTPException(status_code=403, detail="Verification failed")
