"""Offline verification for Martin's WhatsApp tools.

Proves, with NO network calls and WHATSAPP_ENABLED=false:
  1. The 4 tools register into the central ToolRegistry
  2. Sends return a well-formed confirm-then-execute envelope (action_type, payload)
  3. Phone numbers normalize to chatIds; group ids map to @g.us
  4. With WhatsApp disabled, the service simulates sends (never hits the network)

Run:  PYTHONPATH=. .venv/bin/python scripts/test_whatsapp_tools.py
"""
import asyncio

from app.tools.whatsapp_tools import (
    send_whatsapp_message, send_whatsapp_to_group, WHATSAPP_TOOLS,
)
from app.services.whatsapp_service import to_chat_id, get_whatsapp_service

failures = []


def check(label, got, expected):
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f"  (expected {expected!r})"))
    if not ok:
        failures.append(label)


async def main():
    print("\n=== 1. Tools register in ToolRegistry ===")
    from app.tools.tool_registry import ToolRegistry
    reg = ToolRegistry()
    reg.register_all()
    names = set(reg._tools.keys())
    for t in ["send_whatsapp_message", "send_whatsapp_to_group", "list_whatsapp_groups", "check_whatsapp_number"]:
        check(f"registered: {t}", t in names, True)
    check("WHATSAPP_TOOLS count", len(WHATSAPP_TOOLS), 4)

    print("\n=== 2. send_whatsapp_message -> confirmation envelope ===")
    env = await send_whatsapp_message("+254 797 298565", "Hello from Martin")
    check("status", env.get("status"), "confirmation_required")
    check("action_type", env.get("action_type"), "send_whatsapp_message")
    check("confirm_endpoint", env.get("confirm_endpoint"), "/api/v1/agents/execute")
    check("irreversible", env.get("irreversible"), True)
    check("payload.chat_id normalized", env["payload"]["chat_id"], "254797298565@c.us")
    check("has action_id", bool(env.get("action_id")), True)
    print(f"  [info] summary: {env.get('summary')}")

    print("\n=== 3. group send + chatId normalization ===")
    genv = await send_whatsapp_to_group("120363000000000000", "Reminder")
    check("group action_type", genv.get("action_type"), "send_whatsapp_to_group")
    check("group chat_id -> @g.us", genv["payload"]["chat_id"], "120363000000000000@g.us")
    check("to_chat_id passthrough @c.us", to_chat_id("254797298565@c.us"), "254797298565@c.us")
    check("to_chat_id strips +/spaces", to_chat_id("+254 797 298565"), "254797298565@c.us")

    print("\n=== 4. validation guards ===")
    check("empty recipient rejected", (await send_whatsapp_message("", "hi")).get("status"), "error")
    check("empty message rejected", (await send_whatsapp_message("254...", "")).get("status"), "error")

    print("\n=== 5. service simulates when disabled (no network) ===")
    res = await get_whatsapp_service().send_text("+254797298565", "test")
    check("disabled -> simulated", res.get("status"), "simulated")
    check("disabled -> not delivered", res.get("delivered"), False)

    print("\n" + ("=" * 48))
    if failures:
        print(f"RESULT: {len(failures)} FAILED -> {failures}")
        raise SystemExit(1)
    print("RESULT: ALL CHECKS PASSED (nothing sent)")


asyncio.run(main())
