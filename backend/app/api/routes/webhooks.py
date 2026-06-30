import base64
import hashlib
import hmac
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from app.core.config import settings
from app.services.attendee_service import attendee_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_attendee_signature(payload: Dict[str, Any], signature: str) -> bool:
    """
    Verify HMAC-SHA256 signature from Attendee webhook.

    Attendee signs the *canonical* JSON (sorted keys, compact separators)
    and base64-encodes the HMAC-SHA256 digest.  The webhook secret stored in
    the project settings is itself base64-encoded and must be decoded first.
    """
    secret_str = settings.ATTENDEE_WEBHOOK_SECRET
    if not secret_str:
        logger.warning("ATTENDEE_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    # Attendee stores the secret as base64; decode it for HMAC key
    try:
        # base64url → standard base64 (replace - with + and _ with /)
        secret_b64 = secret_str.replace("-", "+").replace("_", "/")
        # Add padding if needed
        padding = 4 - len(secret_b64) % 4
        if padding != 4:
            secret_b64 += "=" * padding
        secret_bytes = base64.b64decode(secret_b64)
    except Exception:
        # Fallback: use raw secret bytes if base64 decode fails
        logger.debug("Webhook secret is not base64 — using raw bytes")
        secret_bytes = secret_str.encode()

    # Canonical JSON — must match Attendee's sign_payload()
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    digest = hmac.new(secret_bytes, canonical.encode("utf-8"), hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")

    return hmac.compare_digest(expected, signature)


@router.post("/attendee")
async def attendee_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Attendee webhook events (transcript.update, bot.state_change).
    Verifies HMAC-SHA256 signature before processing.
    """
    raw_body = await request.body()

    # Parse payload first (needed for canonical signature verification)
    try:
        payload: Dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Verify signature. When ATTENDEE_WEBHOOK_SECRET is configured a mismatch is
    # rejected with 401; the only escape hatch is leaving the secret unset, which
    # _verify_attendee_signature() treats as "skip" (and logs a warning).
    signature = request.headers.get("X-Webhook-Signature", "")
    if not _verify_attendee_signature(payload, signature):
        logger.warning(f"Attendee webhook signature mismatch — rejecting (signature={signature[:20]}...)")
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = payload.get("event") or payload.get("trigger", "unknown")
    bot_id = payload.get("bot_id") or payload.get("data", {}).get("bot_id", "unknown")
    logger.info(f"Received Attendee webhook — event={event}, bot_id={bot_id}")

    # Offload processing to background task
    background_tasks.add_task(attendee_service.process_webhook, payload)

    return {"status": "queued"}
