"""WhatsApp gateway client (self-hosted OpenWA API).

Wraps the OpenWA REST API so Martin can send WhatsApp messages and read groups.
Auth is the `X-API-Key` header; messages are sent through a configured session id.
Gated by settings.WHATSAPP_ENABLED — when False, sends are simulated (logged, not
delivered), mirroring the EMAILS_ENABLED pattern used by EmailService.
"""
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def to_chat_id(recipient: str) -> str:
    """Normalize a phone number or chat id into a WhatsApp chatId.

    - Already a chat id ("...@c.us" / "...@g.us") -> returned unchanged.
    - Phone number ("+254 797 298565", "254797298565") -> "<digits>@c.us".
    """
    r = (recipient or "").strip()
    if r.endswith("@c.us") or r.endswith("@g.us"):
        return r
    digits = re.sub(r"\D", "", r)
    return f"{digits}@c.us"


class WhatsAppService:
    """Thin async client over the OpenWA gateway."""

    def __init__(self):
        self.base_url = (settings.WHATSAPP_GATEWAY_URL or "").rstrip("/")
        self.api_key = settings.WHATSAPP_API_KEY
        self.session_id = settings.WHATSAPP_SESSION_ID

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.session_id)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key or "", "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def send_text(self, recipient: str, text: str) -> Dict[str, Any]:
        """Send a text message to a person (number/chatId) or group (@g.us)."""
        chat_id = to_chat_id(recipient)

        # Safety gate: when WhatsApp is disabled, never hit the network.
        if not settings.WHATSAPP_ENABLED:
            logger.info(f"[WhatsApp] disabled — would send to {chat_id}: {text[:60]!r}")
            return {"status": "simulated", "chat_id": chat_id, "delivered": False}

        if not self.configured:
            return {"status": "error", "error": "WhatsApp gateway not configured "
                    "(set WHATSAPP_GATEWAY_URL, WHATSAPP_API_KEY, WHATSAPP_SESSION_ID)"}

        url = f"/sessions/{self.session_id}/messages/send-text"
        try:
            async with self._client() as client:
                resp = await client.post(url, json={"chatId": chat_id, "text": text})
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
            logger.info(f"[WhatsApp] sent to {chat_id}")
            return {"status": "ok", "chat_id": chat_id, "delivered": True, "result": data}
        except httpx.HTTPStatusError as e:
            body = e.response.text[:300] if e.response is not None else ""
            logger.error(f"[WhatsApp] send failed {e.response.status_code}: {body}")
            return {"status": "error", "error": f"HTTP {e.response.status_code}", "detail": body}
        except httpx.HTTPError as e:
            logger.error(f"[WhatsApp] send error: {e}")
            return {"status": "error", "error": str(e)}

    async def list_groups(self) -> Dict[str, Any]:
        """List the groups the connected number belongs to (read-only)."""
        if not self.configured:
            return {"status": "error", "error": "WhatsApp gateway not configured"}
        try:
            async with self._client() as client:
                resp = await client.get(f"/sessions/{self.session_id}/groups")
                resp.raise_for_status()
                groups = resp.json() if resp.content else []
            # Keep the shape small for the LLM: id + name only.
            slim: List[Dict[str, str]] = []
            items = groups if isinstance(groups, list) else groups.get("data", [])
            for g in items:
                slim.append({
                    "id": g.get("id") or g.get("groupId") or g.get("chatId"),
                    "name": g.get("name") or g.get("subject") or g.get("title"),
                })
            return {"status": "ok", "count": len(slim), "groups": slim}
        except httpx.HTTPError as e:
            logger.error(f"[WhatsApp] list_groups error: {e}")
            return {"status": "error", "error": str(e)}

    async def check_number(self, number: str) -> Dict[str, Any]:
        """Check whether a phone number is registered on WhatsApp (read-only)."""
        if not self.configured:
            return {"status": "error", "error": "WhatsApp gateway not configured"}
        digits = re.sub(r"\D", "", number or "")
        try:
            async with self._client() as client:
                resp = await client.get(f"/sessions/{self.session_id}/contacts/check/{digits}")
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
            return {"status": "ok", "number": digits, "result": data}
        except httpx.HTTPError as e:
            logger.error(f"[WhatsApp] check_number error: {e}")
            return {"status": "error", "error": str(e)}


# Singleton
_whatsapp_service: Optional[WhatsAppService] = None


def get_whatsapp_service() -> WhatsAppService:
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
