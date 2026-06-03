"""
Offline verification for the email/calendar identity split.

Proves, with NO network calls, that:
  1. Outbound email sender (From) is EMAIL_FROM  -> Joseph
  2. The .ics ORGANIZER is CALENDAR_ORGANIZER_EMAIL -> noreply@ (calendar account)
  3. calendar_service._send_updates_mode() returns 'none' so Google sends nothing
     unless CALENDAR_SEND_NATIVE_INVITES is on (and TEST_MODE off)
  4. The meeting_invite.html template still renders

Run:  .venv/bin/python scripts/test_invite_identity.py
Nothing is sent anywhere.
"""
import datetime
from icalendar import Calendar

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.calendar_service import calendar_service

failures = []


def check(label, got, expected):
    ok = got == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got!r}" + ("" if ok else f"  (expected {expected!r})"))
    if not ok:
        failures.append(label)


print("\n=== 1. Email sender identity ===")
svc = EmailService()
check("EmailService.from_email", svc.from_email, "joseph.nganga@africacen.org")
check("EmailService.from_name", svc.from_name, "Joseph Nganga")

print("\n=== 2. .ics ORGANIZER (calendar account, not sender) ===")
ics_bytes = svc._create_calendar_invite(
    title="TWG Sync — Local Test",
    description="https://meet.google.com/fake-link",
    start_time=datetime.datetime(2026, 6, 1, 14, 0, 0),
    duration_minutes=60,
    location="Virtual",
    attendees=["alice@example.org", "bob@example.org"],
    meeting_id="local-test-meeting-001",
    method="REQUEST",
    status="CONFIRMED",
)
cal = Calendar.from_ical(ics_bytes)
event = next(c for c in cal.walk() if c.name == "VEVENT")
organizer = str(event.get("organizer"))
organizer_cn = event.get("organizer").params.get("cn")
attendees = [str(a) for a in event.get("attendee")]
uid = str(event.get("uid"))

check("ORGANIZER address", organizer, "MAILTO:noreply@ecowasiisummit.net")
check("ORGANIZER display name", str(organizer_cn), "ECOWAS Summit")
check("CALENDAR method", str(cal.get("method")), "REQUEST")
check("attendee count", len(attendees), 2)
check("stable UID", uid, "local-test-meeting-001@martin-system.ecowas")
print(f"  [info] sender(From)={svc.from_email}  organizer={organizer.replace('MAILTO:','')}  -> decoupled: {svc.from_email not in organizer}")

print("\n=== 3. sendUpdates mode (Google native invites suppressed) ===")
# Current .env: TEST_MODE=true, CALENDAR_SEND_NATIVE_INVITES=false
check("_send_updates_mode() with current .env", calendar_service._send_updates_mode(), "none")

# Simulate production toggles by flipping settings in-memory (no .env change).
orig_test, orig_native = settings.TEST_MODE, settings.CALENDAR_SEND_NATIVE_INVITES
try:
    settings.TEST_MODE = False
    settings.CALENDAR_SEND_NATIVE_INVITES = False
    check("_send_updates_mode() prod + native OFF", calendar_service._send_updates_mode(), "none")
    settings.CALENDAR_SEND_NATIVE_INVITES = True
    check("_send_updates_mode() prod + native ON", calendar_service._send_updates_mode(), "all")
    settings.TEST_MODE = True  # TEST_MODE always wins
    check("_send_updates_mode() TEST_MODE overrides native ON", calendar_service._send_updates_mode(), "none")
finally:
    settings.TEST_MODE, settings.CALENDAR_SEND_NATIVE_INVITES = orig_test, orig_native

print("\n=== 4. Template renders ===")
try:
    html = svc.jinja_env.get_template("meeting_invite.html").render(
        user_name="Valued Participant",
        meeting_title="TWG Sync — Local Test",
        meeting_date="Monday, June 1, 2026",
        meeting_time="2:00 PM UTC",
        location="Virtual",
        video_link="https://meet.google.com/fake-link",
        pillar_name="Energy TWG",
        portal_url="http://localhost:5173/schedule",
    )
    check("meeting_invite.html non-empty", len(html) > 100, True)
except Exception as e:
    print(f"  [FAIL] template render raised: {e}")
    failures.append("template render")

print("\n" + ("=" * 48))
if failures:
    print(f"RESULT: {len(failures)} FAILED -> {failures}")
    raise SystemExit(1)
print("RESULT: ALL CHECKS PASSED")
