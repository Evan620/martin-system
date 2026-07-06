"""TWG × Campaign OS webhook emitter (WAIIS media engine).

When a TWG meeting's minutes are approved/published, this service emits a
PUBLIC-SAFE payload to Campaign OS, which drafts WAIIS-channel posts behind its
own compliance gate + human review. Nothing here auto-publishes.

Three hard safety rules are baked in:

1. NO RAW CONTENT LEAK. ``build_payload`` reads ONLY the chair-approved
   ``public_summary`` block + a few meeting metadata attributes. It never reads
   ``minutes.content``, ``minutes.key_decisions`` or ``meeting.transcript`` — it
   is structurally impossible for raw content to enter the payload.
2. NEVER FAILS THE CALLER. ``emit_minutes_published`` wraps everything in
   try/except and always returns a status dict; it never raises. Minutes
   approval must succeed even if Campaign OS is down. The webhook is a
   side-effect, not a gate.
3. OFF BY DEFAULT. Gated on ``settings.TWG_WEBHOOK_ENABLED`` + presence of a
   ``public_summary`` + ``settings.CAMPAIGN_OS_INGEST_URL``. Emits nothing until
   all three are satisfied.
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fixed event name (idempotency + routing on Martin's side).
WEBHOOK_EVENT = "minutes.published"
# Short timeout — the emit is a best-effort side-effect, never a blocker.
WEBHOOK_TIMEOUT_SECONDS = 5.0


def _humanize_pillar(pillar: Any) -> str:
    """Humanize a TWG pillar into a display string.

    Accepts a ``TWGPillar`` enum (uses its ``.value``) or a raw string, e.g.
    ``critical_minerals_industrialization`` -> "Critical Minerals Industrialization".
    """
    raw = getattr(pillar, "value", pillar)
    return str(raw or "").replace("_", " ").strip().title()


def _date_str(scheduled_at: Any) -> str:
    """Render a datetime/date as YYYY-MM-DD; fall back to a safe string prefix."""
    if scheduled_at is None:
        return ""
    if hasattr(scheduled_at, "date"):
        return scheduled_at.date().isoformat()
    if hasattr(scheduled_at, "isoformat"):
        return scheduled_at.isoformat()[:10]
    return str(scheduled_at)[:10]


def build_payload(meeting: Any, minutes_public_summary: Dict[str, Any], frontend_url: str) -> Dict[str, Any]:
    """Build the PUBLIC-SAFE payload (exactly the 8 contract fields).

    Reads ONLY chair-approved ``public_summary`` fields + meeting metadata. Raw
    minutes content/key_decisions/transcript are never referenced here, so they
    cannot appear in the output.
    """
    summary = minutes_public_summary or {}
    frontend = (frontend_url or "").rstrip("/")

    return {
        "meeting_title": getattr(meeting, "title", "") or "",
        "twg_pillar": _humanize_pillar(getattr(getattr(meeting, "twg", None), "pillar", None)),
        "date": _date_str(getattr(meeting, "scheduled_at", None)),
        "public_highlights": list(summary.get("highlights") or []),
        "public_decisions_milestones": list(summary.get("decisions_milestones") or []),
        "institutions_public": list(summary.get("institutions_public") or []),
        "next_milestone": summary.get("next_milestone") or "",
        "minutes_url": f"{frontend}/meetings/{getattr(meeting, 'id', '')}",
    }


def sign(secret: str, timestamp: Any, raw_body_bytes: bytes) -> str:
    """Compute the ``X-WAIIS-Signature`` value.

    HMAC-SHA256 over the bytes ``f"{timestamp}.{raw_body}"`` with the shared
    secret. Returns ``sha256=<hex>``. Martin recomputes and constant-time
    compares on his side.
    """
    signing_input = f"{timestamp}.".encode("utf-8") + (raw_body_bytes or b"")
    digest = hmac.new((secret or "").encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def emit_minutes_published(
    meeting: Any,
    minutes_public_summary: Optional[Dict[str, Any]],
    frontend_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit the public-safe payload to Campaign OS. NEVER raises.

    Gated (off by default): fires only when ``TWG_WEBHOOK_ENABLED`` is True, a
    ``public_summary`` is present, and ``CAMPAIGN_OS_INGEST_URL`` is configured.
    Any error (config, network, non-2xx) is caught, logged and returned as a
    status dict so the caller's approval flow always succeeds.

    Returns one of:
      {"status": "skipped", "reason": ...}
      {"status": "sent", "status_code": int, "meeting_id": str}
      {"status": "error", "error": str}
    """
    try:
        if not settings.TWG_WEBHOOK_ENABLED:
            return {"status": "skipped", "reason": "disabled"}

        if not minutes_public_summary:
            return {"status": "skipped", "reason": "no_public_summary"}

        ingest_url = (settings.CAMPAIGN_OS_INGEST_URL or "").strip()
        if not ingest_url:
            return {"status": "skipped", "reason": "no_ingest_url"}

        frontend = frontend_url if frontend_url is not None else settings.FRONTEND_URL
        payload = build_payload(meeting, minutes_public_summary, frontend)

        # Sign and POST the EXACT bytes that were signed (content=, not json=)
        # so Martin's recomputed HMAC matches.
        raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = sign(settings.CAMPAIGN_OS_WEBHOOK_SECRET, timestamp, raw_body)
        meeting_id = str(getattr(meeting, "id", ""))

        headers = {
            "Content-Type": "application/json",
            "X-WAIIS-Event": WEBHOOK_EVENT,
            "X-WAIIS-Meeting-Id": meeting_id,
            "X-WAIIS-Timestamp": timestamp,
            "X-WAIIS-Signature": signature,
        }

        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(ingest_url, content=raw_body, headers=headers)
            resp.raise_for_status()

        logger.info(
            "[TWG webhook] emitted %s for meeting %s (HTTP %s)",
            WEBHOOK_EVENT, meeting_id, resp.status_code,
        )
        return {"status": "sent", "status_code": resp.status_code, "meeting_id": meeting_id}

    except Exception as e:  # noqa: BLE001 — must never propagate to the approval flow
        logger.exception("[TWG webhook] emit failed — approval unaffected: %s", e)
        return {"status": "error", "error": str(e)}
