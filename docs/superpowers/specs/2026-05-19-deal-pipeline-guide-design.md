# Deal Pipeline User Guide & Test Protocol — Design Spec
**Date:** 2026-05-19  
**Author:** AI Agent  
**Status:** Approved — ready for implementation

---

## Goal

Produce an AfCEN-branded Word document (.docx) that Carren can use to:
1. Understand how the Deal Pipeline works (full admin view)
2. Run a complete end-to-end test of all 7 stages herself

---

## Approach

**Live Test + Screenshot + Document (Option A)**

Walk a fresh project through all 7 pipeline stages in the browser using Chrome automation. Take a screenshot at each step. Fix any bugs discovered during the run. Assemble everything into a Word doc using the `afcen-docx` skill.

---

## Document Structure

| Section | Title | Content |
|---------|-------|---------|
| Cover | — | AfCEN brand: navy/gold, title, date, CONFIDENTIAL |
| 1 | Overview | What the pipeline is, who uses it, how to navigate to it |
| 2 | Pipeline Board UI | Filter bar, project cards, stats banner, all controls labelled |
| 3 | Creating a Project (Draft) | Add Project button, form fields, submission |
| 4 | Stage: Pipeline | What it means, available actions, how to advance |
| 5 | Stage: Under Review | What it means, available actions, how to advance |
| 6 | Stage: Summit Ready | What it means, available actions, how to advance |
| 7 | Stage: Featured | What it means, Deal Room flag, how to advance |
| 8 | Stage: Negotiation | What it means, available actions, how to advance |
| 9 | Stage: Committed | Final stage, what happens here |
| 10 | Project Detail Page | 5 tabs (Overview, Investors, Financials, Documents, History), AfCEN score card, Rescore, Investment Template Sections A–D |
| 11 | WAIIS Scoring & Weights | 6 criteria, weighted AfCEN score, tune icon modal |
| 12 | Test Checklist | Sign-off table for Carren |

---

## Execution Plan

1. Log into the app (admin account) via Chrome automation
2. Create a fresh test project → screenshot
3. Walk through each stage in order, clicking Advance Stage:
   - Draft → Pipeline → Under Review → Summit Ready → Featured → Negotiation → Committed
4. At each stage: screenshot the pipeline list + project detail
5. Document the Project Detail tabs (Overview, Investors, Financials, Documents, History)
6. Capture the WAIIS weights modal
7. Fix any bugs found during the run before screenshotting
8. Run `afcen-docx` skill to generate the branded Word doc with embedded screenshots
9. Save output to `~/afcen-docs/deal-pipeline-guide.docx`

---

## Technical Stack

- **Browser automation:** Claude-in-Chrome MCP (`mcp__claude-in-chrome__*`)
- **Screenshot capture:** `mcp__claude-in-chrome__browser_take_screenshot` or gif_creator
- **Document generation:** `afcen-docx` skill + `docx` npm v9.6.1 at `~/afcen-docs/node_modules/docx`
- **Image embedding:** `docx` `ImageRun` with PNG screenshots
- **Output path:** `~/afcen-docs/deal-pipeline-guide.docx`

---

## Test Project Details

- **Name:** AfCEN Pipeline Test — [date]
- **Pillar:** agriculture_food_systems (most populated in DB)
- **Investment size:** $15,000,000
- **Purpose:** Temporary test project for guide; can be deleted after

---

## Success Criteria

- All 7 stages successfully reached and screenshotted
- All buttons and actions documented with visual reference
- Generated .docx opens cleanly in Word and Google Docs
- Carren can follow the document and reproduce every step independently
