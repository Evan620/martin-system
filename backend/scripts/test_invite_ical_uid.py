"""
Regression test for the duplicate-meeting bug.

Root cause: the meeting was delivered through two channels with DIFFERENT UIDs —
the Google Calendar event (invitee added as guest) and our own .ics email
(UID = '<meeting_id>@martin-system.ecowas'). Gmail couldn't tell they were the
same event, so it imported the .ics as a SECOND calendar entry.

Fix: when the Google event exists, the .ics must carry that event's real
iCalUID so the two MERGE instead of duplicating.

Run:  PYTHONPATH=. .venv/bin/python scripts/test_invite_ical_uid.py
Nothing is sent; this only builds and parses the .ics bytes.
"""
import datetime
from icalendar import Calendar

from app.services.email_service import email_service

failures = []


def check(label, got, expected):
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f"  (expected {expected!r})"))
    if not ok:
        failures.append(label)


MEETING_ID = "dba1d612-86fb-4c46-8a34-fbf62afbb693"
GOOGLE_ICAL_UID = "abc123def456@google.com"

print("\n=== 1. With a Google iCalUID, the .ics UID must match it (so Gmail merges) ===")
ics = email_service._create_calendar_invite(
    title="test meeting",
    description="https://meet.google.com/nyw-jrof-cmw",
    start_time=datetime.datetime(2026, 6, 8, 11, 31, 0),
    duration_minutes=60,
    location="Virtual",
    attendees=["lazarusogero1@gmail.com"],
    meeting_id=MEETING_ID,
    ical_uid=GOOGLE_ICAL_UID,
)
event = next(c for c in Calendar.from_ical(ics).walk() if c.name == "VEVENT")
check(".ics UID == Google iCalUID", str(event.get("uid")), GOOGLE_ICAL_UID)

print("\n=== 2. Without a Google iCalUID, fall back to the deterministic UID (backward compat) ===")
ics2 = email_service._create_calendar_invite(
    title="test meeting",
    description="d",
    start_time=datetime.datetime(2026, 6, 8, 11, 31, 0),
    duration_minutes=60,
    location="Virtual",
    attendees=["x@example.org"],
    meeting_id=MEETING_ID,
)
event2 = next(c for c in Calendar.from_ical(ics2).walk() if c.name == "VEVENT")
check("fallback UID unchanged", str(event2.get("uid")), f"{MEETING_ID}@martin-system.ecowas")

print("\n" + ("=" * 48))
if failures:
    print(f"RESULT: {len(failures)} FAILED -> {failures}")
    raise SystemExit(1)
print("RESULT: ALL CHECKS PASSED")
