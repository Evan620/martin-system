import hashlib
import hmac
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from app.core.config import settings
from app.services.attendee_service import attendee_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_attendee_signature(raw_body: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from Attendee webhook."""
    if not settings.ATTENDEE_WEBHOOK_SECRET:
        logger.warning("ATTENDEE_WEBHOOK_SECRET not set — skipping signature verification")
        return True
    expected = hmac.new(
        settings.ATTENDEE_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/attendee")
async def attendee_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Attendee webhook events (transcript.update, bot.state_change).
    Verifies HMAC-SHA256 signature before processing.
    """
    raw_body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Webhook-Signature", "")
    if not _verify_attendee_signature(raw_body, signature):
        logger.warning("Invalid Attendee webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    import json
    try:
        payload: Dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "unknown")
    bot_id = payload.get("bot_id") or payload.get("data", {}).get("bot_id", "unknown")
    logger.info(f"Received Attendee webhook — event={event}, bot_id={bot_id}")

    # Offload processing to background task
    background_tasks.add_task(attendee_service.process_webhook, payload)

    return {"status": "queued"}
