"""
Local end-to-end render of a meeting invite through the REAL send code,
with the SMTP transport monkeypatched so nothing connects or sends.

Exercises email_service.send_meeting_invite() exactly as meetings.py calls it,
captures the fully-built MIME message, and asserts:
  - From: header is Joseph (EMAIL_FROM)
  - a text/calendar attachment exists
  - that .ics is ORGANIZED by noreply@ (CALENDAR_ORGANIZER_EMAIL)

Dumps the .eml and .ics to /tmp for visual inspection. Nothing is sent.
Run:  PYTHONPATH=. .venv/bin/python scripts/test_invite_render.py
"""
import asyncio
import datetime
import smtplib
from email import message_from_string
from icalendar import Calendar

from app.core.config import settings
from app.services.email_service import email_service

captured = {}


class _FakeSMTP:
    """Stand-in for smtplib.SMTP — records the message, never touches the network."""
    def __init__(self, host=None, port=None, *a, **k):
        captured["host"], captured["port"] = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, *a, **k):
        captured["starttls"] = True

    def login(self, *a, **k):
        captured["login"] = a[:1]  # username only

    def sendmail(self, from_addr, to_addrs, msg):
        captured["envelope_from"] = from_addr
        captured["envelope_to"] = to_addrs
        captured["raw"] = msg


async def main():
    # Force the SMTP path + emails-on for this run only (no .env edits, no network).
    settings.EMAILS_ENABLED = True
    settings.SMTP_TLS = False
    email_service.use_resend = False
    email_service.smtp_user = email_service.smtp_user or "user"
    email_service.smtp_password = email_service.smtp_password or "pass"
    smtplib.SMTP = _FakeSMTP

    await email_service.send_meeting_invite(
        to_emails=["alice@example.org", "bob@example.org"],
        subject="Meeting Invitation: TWG Sync — Local Test",
        template_name="meeting_invite.html",
        template_context={
            "user_name": "Valued Participant",
            "meeting_title": "TWG Sync — Local Test",
            "meeting_date": "Monday, June 1, 2026",
            "meeting_time": "2:00 PM UTC",
            "location": "Virtual",
            "video_link": "https://meet.google.com/fake-link",
            "pillar_name": "Energy TWG",
            "portal_url": "http://localhost:5173/schedule",
        },
        meeting_details={
            "title": "TWG Sync — Local Test",
            "meeting_id": "local-test-meeting-001",
            "start_time": datetime.datetime(2026, 6, 1, 14, 0, 0),
            "duration": 60,
            "location": "https://meet.google.com/fake-link",
        },
    )

    raw = captured.get("raw")
    assert raw, "No message was captured — send path did not reach SMTP."
    msg = message_from_string(raw)

    print("\n=== Captured outbound message (NOT sent) ===")
    print("  From:            ", msg["From"])
    print("  To:              ", msg["To"])
    print("  Subject:         ", msg["Subject"])
    print("  envelope from:   ", captured["envelope_from"])
    print("  SMTP connect to: ", f'{captured["host"]}:{captured["port"]}', "(intercepted, no real connection)")

    failures = []

    def check(label, got, expected):
        ok = got == expected
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}")
        if not ok:
            failures.append(label)

    check("From header", msg["From"], "Joseph Nganga <joseph.nganga@africacen.org>")
    check("envelope from", captured["envelope_from"], "joseph.nganga@africacen.org")

    parts = list(msg.walk())
    ics_parts = [p for p in parts if p.get_content_type() == "text/calendar"]
    check("has .ics attachment", len(ics_parts) >= 1, True)

    ics_bytes = ics_parts[0].get_payload(decode=True)
    cal = Calendar.from_ical(ics_bytes)
    event = next(c for c in cal.walk() if c.name == "VEVENT")
    organizer = str(event.get("organizer"))
    check("ics ORGANIZER", organizer, "MAILTO:noreply@ecowasiisummit.net")
    print(f"  [info] From=Joseph, .ics ORGANIZER=noreply@  -> identities decoupled in a real message")

    # Dump for visual inspection
    with open("/tmp/invite_preview.eml", "w") as f:
        f.write(raw)
    with open("/tmp/invite_preview.ics", "wb") as f:
        f.write(ics_bytes)
    print("\n  Wrote /tmp/invite_preview.eml and /tmp/invite_preview.ics for inspection.")

    print("\n" + ("=" * 48))
    if failures:
        print(f"RESULT: {len(failures)} FAILED -> {failures}")
        raise SystemExit(1)
    print("RESULT: ALL CHECKS PASSED (no email sent)")


asyncio.run(main())
