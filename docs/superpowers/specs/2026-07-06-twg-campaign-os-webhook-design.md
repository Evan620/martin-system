# TWG Workspace × Campaign OS — WAIIS Media Engine (Lazarus side)

**Date:** 2026-07-06
**Author:** Lazarus Magwaro (via Claude Code)
**Source of truth:** Joseph Nganga's *Integration Spec v1* (emailed 2026-07-03 03:46 EAT on thread "TWG Workspace × Campaign OS — WAIIS media engine")
**Scope:** the TWG Workspace (this repo, Railway `ravishing-presence`) side only — Tasks assigned to Lazarus. Martin owns Campaign OS (`web-production-2f84d`): the `/api/ingest/twg-meeting` receiver, drafting templates, compliance gate, review email.

---

## 1. Goal

When a TWG meeting's minutes are **approved & published**, emit a **public-safe** payload to Campaign OS, which drafts WAIIS-channel posts (LinkedIn / X / Instagram), runs the compliance gate, and queues them for Joseph's review. **Nothing auto-publishes.** The raw minutes / Otter transcript **never** cross the wire — only a chair-approved public summary.

## 2. The two deliverables (this repo)

### Task 1 — "Public summary" field on the minutes flow
A structured, chair-approved block authored alongside the minutes. This block — never raw minutes/transcripts — is what crosses the wire.

Shape (`public_summary`):
```json
{
  "highlights": ["3–5 bullets, chair-approved"],
  "decisions_milestones": ["only items marked public"],
  "institutions_public": ["only orgs that consented to being named"],
  "next_milestone": "…"
}
```
- Stored on the `minutes` row (new nullable column, JSON — matching the repo's existing JSON-column convention so SQLite tests + Postgres prod both work).
- Authored/edited in the minutes editor (backend update endpoint + frontend section).
- **Chair approval is implicit in the existing `approve_minutes` step** (already Secretariat/chair-gated). No separate approval workflow — approving the minutes approves the public summary with them. This matches the spec ("the chair approves alongside the minutes").

### Task 2 — Webhook emitter on minutes publication
In `approve_minutes` (`backend/app/api/routes/meetings.py`), immediately after status → `APPROVED` and the existing post-approval workflows, emit the payload.

**Exact payload contract (from the spec — public-safe fields ONLY):**
```json
{
  "meeting_title": "WAIIS-2026 TWG — Strategic Minerals",
  "twg_pillar": "Strategic Minerals",
  "date": "2026-07-02",
  "public_highlights": ["…"],
  "public_decisions_milestones": ["…"],
  "institutions_public": ["…"],
  "next_milestone": "…",
  "minutes_url": "…"
}
```
Field mapping:
- `meeting_title` ← `meeting.title`
- `twg_pillar` ← `meeting.twg.pillar` (humanized, e.g. `STRATEGIC_MINERALS` → "Strategic Minerals")
- `date` ← `meeting.scheduled_at` → `YYYY-MM-DD`
- `public_highlights` ← `public_summary.highlights`
- `public_decisions_milestones` ← `public_summary.decisions_milestones`
- `institutions_public` ← `public_summary.institutions_public`
- `next_milestone` ← `public_summary.next_milestone`
- `minutes_url` ← `{FRONTEND_URL}/meetings/{meeting_id}`

**Service-to-service auth — signed webhook secret (Lazarus + Martin joint item).**
HMAC-SHA256 over `"{timestamp}.{raw_body_bytes}"` with a shared secret. Headers on the POST:
| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-WAIIS-Event` | `minutes.published` |
| `X-WAIIS-Meeting-Id` | `<meeting uuid>` (idempotency key for Martin's dedupe) |
| `X-WAIIS-Timestamp` | unix seconds |
| `X-WAIIS-Signature` | `sha256=<hex hmac>` |

Verification (Martin's side): recompute `hmac_sha256(secret, f"{X-WAIIS-Timestamp}.{raw_body}")`, constant-time compare to the hex in `X-WAIIS-Signature`; reject if the timestamp is older than a few minutes (replay guard).

## 3. Non-negotiable safety rules (baked in)

1. **No raw content leak.** The payload builder reads ONLY `public_summary` + meeting metadata. It must be structurally impossible for `minutes.content`, `key_decisions`, or any transcript to enter the payload. (Adversarially verified.)
2. **Approval never fails on webhook error.** The emit is wrapped so any exception (network, config, Campaign OS 500) is caught, logged, and audited — `approve_minutes` still returns success. The webhook is a side-effect, not a gate.
3. **OFF by default.** New config: `TWG_WEBHOOK_ENABLED` (default `False`), `CAMPAIGN_OS_INGEST_URL`, `CAMPAIGN_OS_WEBHOOK_SECRET`. Nothing fires until (a) the Railway → AfCEN-org migration is done and (b) Martin's endpoint + shared secret exist. Also skip the emit if there is no `public_summary` on the minutes.
4. **No auto-publish anywhere.** This side only *emits*; publishing stays behind Campaign OS's compliance gate + Joseph's review link.

## 4. Files & ownership (build waves)

**Wave 1 (parallel, disjoint files):**
- **Data:** `models.py` (add `Minutes.public_summary` JSON, nullable) + new Alembic migration chaining off head `r12_subgroup_links_20260630` + `PublicSummary` Pydantic schema in the repo's schemas module (NOT in `meetings.py`).
- **Service:** new `app/services/twg_webhook_service.py` — pure payload builder + HMAC signer + gated async emitter + unit tests (new test file). Also defines/reads the new config flags in `config.py`.
- **Frontend:** minutes editor — a "Public summary" section (highlights list, decisions/milestones list, public institutions list, next milestone) included in the save payload.

**Wave 2 (single owner of `meetings.py`, after Wave 1):**
- Extend the minutes update endpoint to accept/persist `public_summary`.
- Call `twg_webhook_service.emit_minutes_published(...)` inside `approve_minutes` after `APPROVED` (gated, non-blocking, audited).
- Integration tests (new test file).

## 5. Testing (TDD)

- Payload builder: emits exactly the 8 spec fields; **leak test** asserts raw `content`/`key_decisions`/transcript never appear even if present on the model.
- HMAC signer: deterministic signature; verification round-trips; wrong secret fails.
- Gating: `TWG_WEBHOOK_ENABLED=False` → no HTTP call; missing `public_summary` → no call.
- Non-blocking: emitter raises internally → `approve_minutes` still returns 200.
- Endpoint: persists `public_summary`; approve triggers emit exactly once with the right payload (HTTP mocked).

## 6. Out of scope (flagged, not built here)

- **Task 3 — Railway/repo → AfCEN-org migration.** Prerequisite before this becomes a production event source. No AfCEN Railway org exists in the current account; escalated by Joseph's 2026-07-05 email (transfer `martin-system` + `attendee` repos to `AfCEN-io` + Railway workspace, response due Wed 2026-07-09). Requires AfCEN-org access the builder doesn't have → **Monday blocker note to Joseph.**
- Martin's side: `/api/ingest/twg-meeting`, drafting templates, compliance gate, review email, Blotato/handles.
- The shared secret value itself (provisioned jointly with Martin; the code reads it from config/env).
