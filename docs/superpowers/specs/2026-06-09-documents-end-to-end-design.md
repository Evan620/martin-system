# Documents (Member App) End-to-End — Design

**Date:** 2026-06-09
**Status:** Approved in brainstorm (Sub-project #2); ready for planning
**Builders:** Lazarus + Claude
**Related:** [Meetings end-to-end](2026-06-09-meetings-end-to-end-design.md), [Meeting detail polish](2026-06-09-meeting-detail-polish-design.md)

---

## 1. Purpose
Wire the member **Documents** screen to live data: list the documents shared with the member's TWG, search/filter them, and open them — **PDFs in an in-app viewer**, other types externally. The **✦ Summarise** action is built but lands with Martin (#4).

## 2. Backend (verified — no backend change needed)
- **List:** `GET /api/v1/documents/` (`documents.py:199`). Auth `get_current_active_user`. Member-scoped: returns docs from the user's TWGs **+ global (`twg_id == null`)**; excludes `transcript`/`transcript_placeholder`/`shared_workspace`. Optional `twg_id`, `skip`, `limit`; `X-Total-Count` header.
  - `DocumentRead` (`schemas.py:241`): `id, twg_id, file_name, file_type` (MIME), `stage, is_confidential, file_path, uploaded_by{id,email,role}, twg{id,name,...}, created_at`.
- **Open/download:** `GET /api/v1/documents/{id}/download` (`documents.py:292`). Auth + TWG access. Returns a **`StreamingResponse` of file bytes** with `Content-Type: file_type` (so a member must send the **JWT bearer** to fetch). `shared_workspace` docs (excluded from the list anyway) return a redirect JSON instead.
- **Search:** `GET /api/v1/documents/search?query&twg_id` (vector) exists; **not used in v1** — client-side filter is enough for the member's doc set.

## 3. Decisions (brainstorm)
- **Open:** tap a **PDF** → in-app viewer; tap any other type → open externally.
- **✦ Summarise:** present on each doc, but **activates with Martin (#4)** — tapping it before Martin exists routes to the Martin/Home tab (or is a no-op with a hint). No throwaway work.
- **List UX (dense-data best practice):** search field (client-side filter over the loaded list) + **filter chips** (All + the doc's `document_type`/`category` values seen, e.g. Reports/Minutes/Data/Briefs) + a clean glass card list. Persistent nav (from #1) stays.
- **Confidential:** the list endpoint does not filter `is_confidential` for members; v1 **hides `is_confidential == true` docs client-side** (defensive) — note for a future server-side fix.

## 4. Architecture (mirror the meetings feature)
```
features/documents/
  data/
    documents_models.dart      Document (id, name, type(mime), category, twgName, isConfidential, createdAt, uploadedBy)
    documents_repository.dart   listDocuments(); downloadBytes(id) -> Uint8List; throws DocumentException
  application/
    documents_controller.dart   documentsRepositoryProvider; NotifierProvider + sealed DocumentsState; client-side search+filter helpers
  presentation/
    documents_screen.dart       rewire the seed screen to live data (search + chips + cards)
    pdf_viewer_screen.dart       in-app PDF viewer (fetch bytes with bearer, render)
```
- **Repository** reuses `dioProvider` (bearer interceptor). `downloadBytes(id)` calls `GET /documents/$id/download` with `responseType: ResponseType.bytes` → `Uint8List`.
- **Open behavior:** `isPdf = type contains 'pdf'`. PDF → push `pdf_viewer_screen` (in-app). Non-PDF → `downloadBytes` → write to a temp file (`path_provider`) → `OpenFilex.open(path)`.
- **PDF viewer:** `pdfx` (`PdfController(document: PdfDocument.openData(bytes))`) on a Sovereign scaffold, with loading/error states; bytes fetched via the repo (so the bearer token is applied).
- **Controller:** `DocumentsState` sealed = `loading | data(List<Document>) | error | empty`. Holds the full list; the screen filters by search text + selected chip locally.
- **Routing:** the Documents branch (created in #1's StatefulShellRoute) gets a nested `documents/:id/pdf` route using `sovereignPage` for the viewer (keeps the nav persistent), or a plain push — prefer the nested branch route for nav persistence.

Dependencies to add: `pdfx`, `open_filex`, `path_provider`.

## 5. UX states
Loading (gold spinner) · error (message + Retry) · empty ("No documents shared yet") · offline (error state). PDF viewer: loading / render / error. Non-PDF open: brief progress then hand off to the OS; on failure, a SnackBar.

## 6. Testing
- Model: `Document.fromJson` (mime → type, category, confidential, twg name).
- Repository: `listDocuments` parses a list (mocked Dio); `downloadBytes` requests with `ResponseType.bytes`; error → `DocumentException`.
- Controller: state transitions; the search+filter helper narrows the list correctly (by name + by chip/category); confidential hidden.
- Widget: list renders a doc name from live data; typing filters; tapping a PDF card pushes the viewer route.

## 7. Out of scope / deferred
Server-side vector search, the ✦ Summarise result (Martin #4), member upload, confidential server-side filtering, offline caching.

## 8. Risks
- `pdfx` native setup (Android minSdk / iOS) — confirm Android builds; it's pure-Dart rendering via PDFium, usually fine on the existing Android toolchain.
- Non-PDF "open externally" needs bytes→temp→`OpenFilex`; if a type has no handler app, show a graceful SnackBar.
