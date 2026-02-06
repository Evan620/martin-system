from fastapi import APIRouter, Header, HTTPException, Request, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import logging
from app.services.fireflies_service import fireflies_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/fireflies")
async def fireflies_webhook(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Handle Fireflies.ai Webhook events.
    Fireflies sends: {"meetingId": "...", "eventType": "Transcription completed"}
    """
    meeting_id = payload.get("meetingId", "unknown")
    event_type = payload.get("eventType", "unknown")
    logger.info(f"Received Fireflies webhook — meetingId={meeting_id}, eventType={event_type!r}")

    if event_type != "Transcription completed":
        logger.info(f"Ignoring non-transcription webhook event: {event_type}")
        return {"status": "ignored", "reason": f"Event type '{event_type}' not handled"}

    # Offload processing to background task to respond quickly to the webhook
    background_tasks.add_task(fireflies_service.process_webhook, payload)

    return {"status": "queued"}
