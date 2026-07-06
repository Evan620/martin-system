# TWG → Campaign OS webhook — contract & handoff (for Martin)

**From:** Lazarus (TWG Workspace side) · **To:** Martin Maina (Campaign OS side)
**Status (2026-07-06):** The TWG-side emitter is **built, deployed, and gated OFF** in production. It fires nothing until (a) the shared secret + your endpoint URL are set, and (b) `TWG_WEBHOOK_ENABLED=true`. Build to this contract and we align without further round-trips.
**Ref:** Joseph's *Integration Spec v1* (2026-07-03). This doc is the concrete wire contract for the one piece we share.

---

## What fires, and when

When a TWG meeting's minutes are **approved & published** in the TWG Workspace (the existing chair/Secretariat approval step), we `POST` a **public-safe** payload to your ingest endpoint. One-directional, best-effort, no auto-publish anywhere on our side.

- **Only** the chair-approved *Public summary* block crosses the wire. Raw minutes, `key_decisions`, and Otter transcripts are **structurally excluded** — the payload builder reads a fixed whitelist, verified by unit tests + a leak probe.
- Emit is a **non-blocking side-effect**: if your endpoint is down, minutes approval still succeeds. We do **not** retry in v1.
- Skipped automatically when a meeting has no Public summary.

## Endpoint you build

```
POST /api/ingest/twg-meeting
```

### Request body — exactly these 8 keys (public-safe)
```json
{
  "meeting_title": "WAIIS-2026 TWG — Strategic Minerals",
  "twg_pillar": "Strategic Minerals",
  "date": "2026-07-02",
  "public_highlights": ["3–5 chair-approved bullets"],
  "public_decisions_milestones": ["only items cleared for public release"],
  "institutions_public": ["only orgs that consented to being named"],
  "next_milestone": "…",
  "minutes_url": "https://<twg-frontend>/meetings/<meeting_id>"
}
```

### Headers (5)
```
Content-Type:       application/json
X-WAIIS-Event:      minutes.published
X-WAIIS-Meeting-Id: <uuid>            # stable per meeting → your idempotency/dedupe key
X-WAIIS-Timestamp:  <unix seconds, integer as string>
X-WAIIS-Signature:  sha256=<hex>
```

## HMAC verification (do this before trusting the body)

Signature = HMAC-SHA256 over the bytes `f"{timestamp}.{raw_body}"`, where `raw_body` is the **exact raw request bytes as received** — verify against the raw bytes, do **not** parse-then-re-serialize (we sign the same bytes we POST).

```python
import hmac, hashlib, time

def verify(raw_body: bytes, timestamp: str, signature_header: str, secret: str) -> bool:
    # 1. replay guard — reject stale/absent timestamps (±5 min)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (TypeError, ValueError):
        return False
    # 2. recompute over the EXACT raw bytes
    signing_input = f"{timestamp}.".encode("utf-8") + raw_body
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()
    # 3. constant-time compare (never ==)
    return hmac.compare_digest(expected, signature_header or "")
```

The `secret` must equal `CAMPAIGN_OS_WEBHOOK_SECRET` on our side (we agree one value, set it on both platforms).

## Your side (from Joseph's spec — for context, not our scope)

- `/api/ingest/twg-meeting` → drafting engine → per-channel templates (LinkedIn recap, X thread, IG caption + brand card) → compliance gate → **one review email per meeting bundling all 3 channel drafts** into the normal Joseph review-link flow.
- Editorial rules live in your compliance gate (real-anchor rule, WAIIS-Secretariat voice, consent, status-language guardrails, never source from raw transcripts).
- Nothing auto-publishes — everything stops at the compliance gate then Joseph's review.

## To go live (rollout order)

1. **AfCEN-org migration first** (Joseph's prerequisite — Lazarus): TWG Workspace off the personal Railway/GitHub onto the AfCEN org before it's a production event source.
2. Agree + set the shared secret on both platforms; you deploy `/api/ingest/twg-meeting`.
3. On our side: set `CAMPAIGN_OS_INGEST_URL` + `CAMPAIGN_OS_WEBHOOK_SECRET`, then flip `TWG_WEBHOOK_ENABLED=true` **last**.
4. Until then: the manual bridge (per Joseph) — published summaries hand-carried into Campaign OS review.

## Reference (our emitter)

`backend/app/services/twg_webhook_service.py` — `build_payload()` (the 8-key whitelist), `sign()` (the exact scheme above), `emit_minutes_published()` (gated, never raises). Wired into `approve_minutes` in `backend/app/api/routes/meetings.py`. Migration `r13_public_summary_20260706` adds `minutes.public_summary`.
