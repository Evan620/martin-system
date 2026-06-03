"""WhatsApp tools for Martin.

- Sends (send_whatsapp_message, send_whatsapp_to_group) are OUTWARD-FACING, so they
  use the confirm-then-execute pattern: the tool returns a `confirmation_required`
  envelope (propose_action); the real delivery happens in routes/agents.py
  (_execute_send_whatsapp_*) only after the user confirms.
- Reads (list_whatsapp_groups, check_whatsapp_number) return data directly.
"""
from typing import Any, Dict

from app.services.whatsapp_service import get_whatsapp_service, to_chat_id
from app.tools._rbac import propose_action


# --- Outward-facing: confirm-then-execute -----------------------------------

async def send_whatsapp_message(to: str, message: str) -> Dict[str, Any]:
    """Propose sending a WhatsApp message to a person (number or chatId)."""
    if not to or not str(to).strip():
        return {"status": "error", "error": "A recipient (phone number) is required."}
    if not message or not str(message).strip():
        return {"status": "error", "error": "Message text is required."}

    chat_id = to_chat_id(to)
    preview = message if len(message) <= 80 else message[:77] + "..."
    return propose_action(
        action_type="send_whatsapp_message",
        summary=f'Send WhatsApp to {to}: "{preview}"',
        payload={"chat_id": chat_id, "to": to, "message": message},
        irreversible=True,  # a sent message can't be unsent
    )


async def send_whatsapp_to_group(group: str, message: str) -> Dict[str, Any]:
    """Propose posting a WhatsApp message to a group (group id "...@g.us")."""
    if not group or not str(group).strip():
        return {"status": "error", "error": "A group id is required (use list_whatsapp_groups)."}
    if not message or not str(message).strip():
        return {"status": "error", "error": "Message text is required."}

    chat_id = group.strip() if group.strip().endswith("@g.us") else f"{group.strip()}@g.us"
    preview = message if len(message) <= 80 else message[:77] + "..."
    return propose_action(
        action_type="send_whatsapp_to_group",
        summary=f'Post WhatsApp to group {group}: "{preview}"',
        payload={"chat_id": chat_id, "group": group, "message": message},
        irreversible=True,
    )


# --- Read-only --------------------------------------------------------------

async def list_whatsapp_groups() -> Dict[str, Any]:
    """List the WhatsApp groups Martin's number belongs to."""
    return await get_whatsapp_service().list_groups()


async def check_whatsapp_number(number: str) -> Dict[str, Any]:
    """Check whether a phone number is registered on WhatsApp."""
    if not number or not str(number).strip():
        return {"status": "error", "error": "A phone number is required."}
    return await get_whatsapp_service().check_number(number)


# --- Tool definitions (name/description/schema for the registry) ------------

SEND_WHATSAPP_MESSAGE_TOOL = {
    "function": {
        "name": "send_whatsapp_message",
        "description": (
            "Send a WhatsApp message to a person. Requires user confirmation before "
            "it is actually delivered. Use for 1:1 outreach to a phone number."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient phone number in international format (e.g. +254797298565)"},
                "message": {"type": "string", "description": "The message text to send"},
            },
            "required": ["to", "message"],
        },
    }
}

SEND_WHATSAPP_TO_GROUP_TOOL = {
    "function": {
        "name": "send_whatsapp_to_group",
        "description": (
            "Post a WhatsApp message to a group. Requires user confirmation before "
            "delivery. Get the group id from list_whatsapp_groups first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "group": {"type": "string", "description": "Group id (ends with @g.us)"},
                "message": {"type": "string", "description": "The message text to post"},
            },
            "required": ["group", "message"],
        },
    }
}

LIST_WHATSAPP_GROUPS_TOOL = {
    "function": {
        "name": "list_whatsapp_groups",
        "description": "List the WhatsApp groups the connected number is a member of (id + name). Read-only.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }
}

CHECK_WHATSAPP_NUMBER_TOOL = {
    "function": {
        "name": "check_whatsapp_number",
        "description": "Check whether a phone number is registered on WhatsApp before messaging it. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {"type": "string", "description": "Phone number in international format"},
            },
            "required": ["number"],
        },
    }
}

WHATSAPP_TOOLS = [
    (SEND_WHATSAPP_MESSAGE_TOOL, send_whatsapp_message),
    (SEND_WHATSAPP_TO_GROUP_TOOL, send_whatsapp_to_group),
    (LIST_WHATSAPP_GROUPS_TOOL, list_whatsapp_groups),
    (CHECK_WHATSAPP_NUMBER_TOOL, check_whatsapp_number),
]
