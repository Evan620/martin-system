"""Pure unit tests for the TWG × Campaign OS webhook service.

No DB, no real network. Covers the 4 hard rules from the Integration Spec:
exact 8-field payload, NO raw-content leak, deterministic/verifiable HMAC,
off-by-default gating, and never-raises emit behaviour.
"""
import hashlib
import hmac
import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import twg_webhook_service as svc
from app.services.twg_webhook_service import build_payload, sign, emit_minutes_published

EXPECTED_FIELDS = {
    "meeting_title",
    "twg_pillar",
    "date",
    "public_highlights",
    "public_decisions_milestones",
    "institutions_public",
    "next_milestone",
    "minutes_url",
}

SECRET_TEXT = "raw-minutes-should-never-appear-Otter-transcript-body-XYZ"


def _meeting_with_content():
    """A meeting/minutes-like object that CARRIES raw content on purpose.

    The leak test asserts none of these secret-bearing attributes surface in
    the payload even though they are present on the objects.
    """
    twg = SimpleNamespace(pillar="critical_minerals_industrialization")
    return SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        title="WAIIS-2026 TWG — Critical Minerals",
        scheduled_at=datetime(2026, 7, 2, 14, 30, 0),
        twg=twg,
        # Raw content that MUST NOT leak:
        transcript=SECRET_TEXT,
        content=SECRET_TEXT,
        key_decisions=SECRET_TEXT,
        minutes=SimpleNamespace(content=SECRET_TEXT, key_decisions=SECRET_TEXT),
    )


def _public_summary():
    return {
        "highlights": ["Signed MoU on cross-border grid", "Agreed 2027 pilot"],
        "decisions_milestones": ["Milestone A approved"],
        "institutions_public": ["ECOWAS Commission", "AfDB"],
        "next_milestone": "Ministerial review Q4",
    }


# ---------------------------------------------------------------------------
# build_payload
# ---------------------------------------------------------------------------

def test_payload_has_exactly_the_eight_fields():
    payload = build_payload(_meeting_with_content(), _public_summary(), "https://twg.example")
    assert set(payload.keys()) == EXPECTED_FIELDS


def test_payload_maps_metadata_and_summary():
    payload = build_payload(_meeting_with_content(), _public_summary(), "https://twg.example/")
    assert payload["meeting_title"] == "WAIIS-2026 TWG — Critical Minerals"
    # pillar humanized from the enum-style value
    assert payload["twg_pillar"] == "Critical Minerals Industrialization"
    assert payload["date"] == "2026-07-02"
    assert payload["public_highlights"] == ["Signed MoU on cross-border grid", "Agreed 2027 pilot"]
    assert payload["public_decisions_milestones"] == ["Milestone A approved"]
    assert payload["institutions_public"] == ["ECOWAS Commission", "AfDB"]
    assert payload["next_milestone"] == "Ministerial review Q4"
    # trailing slash on frontend_url is normalized
    assert payload["minutes_url"] == "https://twg.example/meetings/11111111-1111-1111-1111-111111111111"


def test_payload_handles_missing_summary_fields():
    payload = build_payload(_meeting_with_content(), {}, "https://twg.example")
    assert payload["public_highlights"] == []
    assert payload["public_decisions_milestones"] == []
    assert payload["institutions_public"] == []
    assert payload["next_milestone"] == ""
    assert set(payload.keys()) == EXPECTED_FIELDS


def test_payload_pillar_accepts_enum_like_object():
    meeting = _meeting_with_content()
    meeting.twg = SimpleNamespace(pillar=SimpleNamespace(value="energy_infrastructure"))
    payload = build_payload(meeting, _public_summary(), "https://twg.example")
    assert payload["twg_pillar"] == "Energy Infrastructure"


def test_LEAK_raw_content_never_appears_in_payload():
    """Even with content/key_decisions/transcript present, none leak."""
    payload = build_payload(_meeting_with_content(), _public_summary(), "https://twg.example")
    serialized = json.dumps(payload)
    assert SECRET_TEXT not in serialized
    assert "transcript" not in payload
    assert "content" not in payload
    assert "key_decisions" not in payload


def test_LEAK_summary_with_extra_keys_does_not_widen_payload():
    """A public_summary carrying stray keys can't smuggle extra fields out."""
    poisoned = _public_summary()
    poisoned["content"] = SECRET_TEXT
    poisoned["raw_transcript"] = SECRET_TEXT
    payload = build_payload(_meeting_with_content(), poisoned, "https://twg.example")
    assert set(payload.keys()) == EXPECTED_FIELDS
    assert SECRET_TEXT not in json.dumps(payload)


# ---------------------------------------------------------------------------
# sign
# ---------------------------------------------------------------------------

def test_sign_is_deterministic_and_prefixed():
    body = b'{"a":1}'
    sig1 = sign("secret", "1720000000", body)
    sig2 = sign("secret", "1720000000", body)
    assert sig1 == sig2
    assert sig1.startswith("sha256=")


def test_sign_verifies_against_independent_recompute():
    body = b'{"meeting_title":"x"}'
    timestamp = "1720000123"
    secret = "shared-secret"
    got = sign(secret, timestamp, body)
    expected_hex = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()
    assert got == f"sha256={expected_hex}"


def test_sign_wrong_secret_fails():
    body = b'{"a":1}'
    good = sign("right-secret", "1720000000", body)
    bad = sign("wrong-secret", "1720000000", body)
    assert good != bad


def test_sign_changes_with_timestamp_and_body():
    body = b'{"a":1}'
    assert sign("s", "1", body) != sign("s", "2", body)
    assert sign("s", "1", body) != sign("s", "1", b'{"a":2}')


# ---------------------------------------------------------------------------
# emit_minutes_published — gating + never-raises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emit_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", False)
    result = await emit_minutes_published(_meeting_with_content(), _public_summary())
    assert result == {"status": "skipped", "reason": "disabled"}


@pytest.mark.asyncio
async def test_emit_skipped_when_no_public_summary(monkeypatch):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "CAMPAIGN_OS_INGEST_URL", "https://campaign.example/api/ingest/twg-meeting")
    result = await emit_minutes_published(_meeting_with_content(), None)
    assert result == {"status": "skipped", "reason": "no_public_summary"}


@pytest.mark.asyncio
async def test_emit_skipped_when_no_ingest_url(monkeypatch):
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "CAMPAIGN_OS_INGEST_URL", "")
    result = await emit_minutes_published(_meeting_with_content(), _public_summary())
    assert result == {"status": "skipped", "reason": "no_ingest_url"}


@pytest.mark.asyncio
async def test_emit_swallows_http_error_and_returns_error(monkeypatch):
    """A raised HTTP/network error must be caught — emit never raises."""
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "CAMPAIGN_OS_INGEST_URL", "https://campaign.example/api/ingest/twg-meeting")
    monkeypatch.setattr(settings, "CAMPAIGN_OS_WEBHOOK_SECRET", "s")

    class _BoomClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            raise svc.httpx.ConnectError("boom")

    monkeypatch.setattr(svc.httpx, "AsyncClient", _BoomClient)

    result = await emit_minutes_published(_meeting_with_content(), _public_summary())
    assert result["status"] == "error"
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_emit_sends_signed_public_safe_payload(monkeypatch):
    """Happy path: posts exactly the signed bytes with the 5 headers, no leak."""
    monkeypatch.setattr(settings, "TWG_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "CAMPAIGN_OS_INGEST_URL", "https://campaign.example/api/ingest/twg-meeting")
    monkeypatch.setattr(settings, "CAMPAIGN_OS_WEBHOOK_SECRET", "shared-secret")

    captured = {}

    class _CaptureClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, content=None, headers=None):
            captured["url"] = url
            captured["content"] = content
            captured["headers"] = headers
            return SimpleNamespace(status_code=200, raise_for_status=lambda: None)

    monkeypatch.setattr(svc.httpx, "AsyncClient", _CaptureClient)

    result = await emit_minutes_published(_meeting_with_content(), _public_summary(), frontend_url="https://twg.example")
    assert result["status"] == "sent"
    assert result["status_code"] == 200

    # 5 required headers present
    h = captured["headers"]
    assert h["Content-Type"] == "application/json"
    assert h["X-WAIIS-Event"] == "minutes.published"
    assert h["X-WAIIS-Meeting-Id"] == "11111111-1111-1111-1111-111111111111"
    assert h["X-WAIIS-Timestamp"].isdigit()
    assert h["X-WAIIS-Signature"].startswith("sha256=")

    # Signature matches the exact bytes posted (round-trip verification).
    expected_sig = sign("shared-secret", h["X-WAIIS-Timestamp"], captured["content"])
    assert h["X-WAIIS-Signature"] == expected_sig

    # No raw content on the wire.
    assert SECRET_TEXT not in captured["content"].decode("utf-8")
    body = json.loads(captured["content"])
    assert set(body.keys()) == EXPECTED_FIELDS
