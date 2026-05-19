# Deal Pipeline Guide — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `~/afcen-docs/deal-pipeline-guide.docx` — an AfCEN-branded Word document with real screenshots walking through all 7 pipeline stages, for Carren.

**Architecture:** Chrome automation captures screenshots at each stage; a Node.js script built with the `afcen-docx` skill assembles them into a branded .docx. Bugs found during the browser run are fixed before screenshotting.

**Tech Stack:** Claude-in-Chrome MCP, afcen-docx skill, docx npm v9.6.1 (`~/afcen-docs/node_modules/docx`)

---

### Task 0: Reset environment

**Files:** None

- [ ] Reset bcrypt password for admin test account
- [ ] Start backend if not running: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- [ ] Start frontend if not running: `cd frontend && npm run dev`
- [ ] Verify both are up: `curl -s http://localhost:8000/health` and `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173`

---

### Task 1: Login + capture Pipeline Board screenshot

**Files:**
- Create: `~/afcen-docs/screenshots/01-pipeline-board.png`

- [ ] Open Chrome tab, navigate to `http://localhost:5173`
- [ ] Inject auth token via JavaScript (fetch login API → store in localStorage)
- [ ] Navigate to `/pipeline`
- [ ] Take screenshot → save as `~/afcen-docs/screenshots/01-pipeline-board.png`

---

### Task 2: Create fresh test project (Draft stage)

**Files:**
- Create: `~/afcen-docs/screenshots/02-add-project-form.png`
- Create: `~/afcen-docs/screenshots/03-draft-in-pipeline.png`

- [ ] Click "Add Project" button → screenshot the form (`02-add-project-form.png`)
- [ ] Fill in:
  - Name: `AfCEN Pipeline Test — May 2026`
  - Description: `Test project for pipeline guide documentation`
  - Investment size: `15000000`
  - Pillar: `agriculture_food_systems`
  - Readiness: `6`, Strategic alignment: `7`
- [ ] Submit and wait for project to appear
- [ ] Screenshot pipeline list showing Draft project (`03-draft-in-pipeline.png`)

---

### Task 3: Open Project Detail + screenshot all tabs

**Files:**
- Create: `~/afcen-docs/screenshots/04-project-detail-overview.png`
- Create: `~/afcen-docs/screenshots/05-project-detail-investors.png`
- Create: `~/afcen-docs/screenshots/06-project-detail-financials.png`
- Create: `~/afcen-docs/screenshots/07-project-detail-documents.png`
- Create: `~/afcen-docs/screenshots/08-project-detail-history.png`

- [ ] Click the test project to open detail page
- [ ] Screenshot Overview tab (`04-project-detail-overview.png`)
- [ ] Click Investors tab → screenshot (`05-project-detail-investors.png`)
- [ ] Click Financials tab → screenshot (`06-project-detail-financials.png`)
- [ ] Click Documents tab → screenshot (`07-project-detail-documents.png`)
- [ ] Click History tab → screenshot (`08-project-detail-history.png`)

---

### Task 4: Advance Draft → Pipeline

**Files:**
- Create: `~/afcen-docs/screenshots/09-advance-stage-modal.png`
- Create: `~/afcen-docs/screenshots/10-pipeline-stage.png`

- [ ] On project detail, click "Advance Stage" button → screenshot modal (`09-advance-stage-modal.png`)
- [ ] Select "Pipeline", add note "Moving to active pipeline", confirm
- [ ] Wait for success, screenshot project now at Pipeline stage (`10-pipeline-stage.png`)
- [ ] Fix any bugs encountered before taking the screenshot

---

### Task 5: Advance Pipeline → Under Review

**Files:**
- Create: `~/afcen-docs/screenshots/11-under-review-stage.png`

- [ ] Click "Advance Stage" → select "Under Review" → confirm
- [ ] Screenshot project at Under Review stage (`11-under-review-stage.png`)
- [ ] Fix any bugs

---

### Task 6: Advance Under Review → Summit Ready

**Files:**
- Create: `~/afcen-docs/screenshots/12-summit-ready-stage.png`
- Create: `~/afcen-docs/screenshots/13-rescore-in-action.png`

- [ ] Click "Advance Stage" → select "Summit Ready" → confirm
- [ ] Screenshot project at Summit Ready stage (`12-summit-ready-stage.png`)
- [ ] Click "Rescore Project" → screenshot spinner/result (`13-rescore-in-action.png`)

---

### Task 7: Advance Summit Ready → Featured (Deal Room)

**Files:**
- Create: `~/afcen-docs/screenshots/14-featured-stage.png`

- [ ] Click "Advance Stage" → select "Featured" → confirm
- [ ] Screenshot project at Featured stage (`14-featured-stage.png`)
- [ ] Note the is_flagship flag behavior if visible

---

### Task 8: Advance Featured → Negotiation

**Files:**
- Create: `~/afcen-docs/screenshots/15-negotiation-stage.png`

- [ ] Click "Advance Stage" → select "Negotiation" → confirm
- [ ] Screenshot project at Negotiation stage (`15-negotiation-stage.png`)

---

### Task 9: Advance Negotiation → Committed

**Files:**
- Create: `~/afcen-docs/screenshots/16-committed-stage.png`

- [ ] Click "Advance Stage" → select "Committed" → confirm
- [ ] Screenshot project at Committed stage — the final state (`16-committed-stage.png`)

---

### Task 10: Capture WAIIS Scoring Weights modal

**Files:**
- Create: `~/afcen-docs/screenshots/17-scoring-weights-modal.png`

- [ ] Return to pipeline list
- [ ] Click the tune icon (⊞) in the filter bar → screenshot weights modal (`17-scoring-weights-modal.png`)
- [ ] Close modal

---

### Task 11: Generate the AfCEN Word document

**Files:**
- Create: `~/afcen-docs/generate-guide.js`
- Create: `~/afcen-docs/deal-pipeline-guide.docx`

- [ ] Invoke `afcen-docx` skill
- [ ] Write `~/afcen-docs/generate-guide.js` using the skill's Quick Start Template
- [ ] Embed all 17 screenshots using `ImageRun` from docx package
- [ ] Structure: cover page + 12 sections + test checklist table
- [ ] Run: `node ~/afcen-docs/generate-guide.js`
- [ ] Verify output: `ls -lh ~/afcen-docs/deal-pipeline-guide.docx`
- [ ] Confirm file opens (check file size > 200KB indicates images embedded)
