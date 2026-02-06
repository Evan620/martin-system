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
    Fireflies sends a POST request when a meeting transcript is ready.
    """
    # Extract identifiers for observability before offloading
    hook_data = payload.get("data", payload)
    transcript_id = hook_data.get("id", "unknown")
    title = hook_data.get("title", "unknown")
    logger.info(f"Received Fireflies webhook — transcript_id={transcript_id}, title={title!r}")

    # Offload processing to background task to respond quickly to the webhook
    background_tasks.add_task(fireflies_service.process_webhook, payload)
    
    return {"status": "queued"}
