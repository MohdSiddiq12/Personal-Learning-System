# Progress

## Phase 2: PDF ingestion core

**Status: Complete**

### Completed

- Added PyMuPDF-backed PDF validation and page-preserving text extraction, with size/page limits and scanned-document detection.
- Added source-byte SHA-256 hashes, sanitized metadata, user-facing ingestion errors, and a CLI demo.
- Added generated-PDF tests for page boundaries, images, encryption, invalid input, limits, hashing, metadata, and untrusted text.
- Zero-byte files are classified as invalid PDFs because they have no `%PDF-` header.

### Validation

- `uv sync`: succeeded on the pinned Python 3.12.4; resolved 19 packages and installed PyMuPDF 1.28.2.
- `uv sync --locked`: succeeded; 19 packages resolved and 18 checked.
- `uv run pytest`: 17 tests passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 17 files already formatted.
- CLI subprocess tests passed for a generated PDF and invalid input.

The core extractor has no OCR; the hosted API adds a killable processing timeout and stricter page limits.

## Phase 3: Local Streamlit demo

**Status: Complete**

### Completed

- Added an in-memory local PDF upload and page browser with search, page navigation, summary, export, session duplicate detection, and OCR warning.
- Added generated text and image-only sample PDFs, AppTest upload coverage, view-model tests, and a marked Playwright browser smoke test.
- Restricted the server to localhost and disabled Streamlit usage statistics.

### Validation

- `uv sync`: succeeded on pinned Python 3.12.4; resolved 58 packages, installed Streamlit 1.65.0 and Playwright 1.63.0.
- `uv sync --locked`: succeeded; resolved 58 packages and checked 56 installed packages.
- `uv run pytest`: 30 passed, 1 browser test deselected.
- `uv run pytest -m e2e`: 1 passed, 30 deselected, using the existing system Chrome without downloading a browser.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 25 files already formatted.
- Live check: `http://localhost:8501/_stcore/health` returned `ok`; `http://localhost:8501/` returned HTTP 200.
- Playwright screenshots: `data/screenshots/success.png` (53,094 bytes) and `data/screenshots/error.png` (44,434 bytes).
- The documented Chromium + headless-shell download estimate is approximately 250-300 MB; it was not installed because system Chrome was available.

The local Streamlit prototype does not write uploads to local disk. The hosted app retains PDFs privately in Supabase. OCR remains unimplemented.

## Phase 4: Public-service deployment foundation

**Status: Implementation scaffolded; external services not configured**

### Completed

- Added a Next.js interface with Supabase email/password auth, private account library, PDF upload/retrieval/deletion, page search/export, and inline page-cited guide display.
- Added a FastAPI service that verifies Supabase access tokens, stores PDFs in a private Storage bucket, persists extracted pages/guides in owner-scoped Postgres rows, and uses signed URLs for retrieval.
- Added process-isolated PDF parsing with a timeout, page/size/text caps, concurrent parser limits, per-account limits, and database-backed per-user upload plus global/user AI-job quotas.
- Added opt-in BYOK Gemini generation with a provider data-use consent gate and page citation validation.
- Added a Supabase migration, Docker/Render API starter, Vercel frontend instructions, a draft terms/takedown page, and API tests.

### Validation

- `uv run pytest`: 42 passed, 1 browser test deselected.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 34 Python files already formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked.
- `npm run lint --prefix web`: passed.
- `npm run build --prefix web`: passed; `/` and `/terms` prerender.
- `npm audit --prefix web`: 0 vulnerabilities.
- Local live smoke: FastAPI `/health` returned `{"status":"ok"}`; `http://localhost:3000/` and `/terms` returned HTTP 200; live CORS allowed the configured localhost origin. The 390px-wide UI rendered the signed-out setup state.
- `.env` and `web/.env.local` are ignored; `web/.env.example` remains trackable. No PDFs are tracked.
- `docker build` was attempted but could not connect because Docker Desktop's Linux engine is not running; the image build is unverified.

No Supabase project, credentials, actual Gemini key, or legal license decision is configured here. Real auth/storage/RLS and provider calls remain unverified. The terms page is explicitly a draft; configure the takedown contact and have counsel review it. No public deployment has been made.

## Product Spec Gap Audit (2026-10-13)

| Capability | Status | Implementation | Test coverage |
| --- | --- | --- | --- |
| Book map generation | Partial | `src/learnbook/api/summary.py`, `src/learnbook/api/schemas.py`, `web/src/app/page.tsx` | Mock schema/citation test ran; real Gemini output is unverified. Output is a flat overview/ideas/frameworks/practice list, not a ranked topic/subtopic map with study times. |
| Whole-book coverage (chunking) | Partial | `src/learnbook/api/summary.py::_page_chunks`, `generate_book_summary` | Synthetic page-marker and long-page chunk tests ran. Full-book coverage/coherence on real provider output is unverified; cap is 400,000 extracted characters. |
| Page-reference validation | Partial | `src/learnbook/api/summary.py::generate_book_summary`, `src/learnbook/api/schemas.py` | Valid page citation test ran. Out-of-range rejection branch and real model citations are unverified; validation checks range, not whether a cited page substantively supports a claim. |
| Preferences screen | Missing | No preferences model or screen; `web/src/app/page.tsx` has no per-topic minutes, daily time, or goal controls. | No test. |
| Learning-path builder | Missing | No path-selection or prerequisite-ordering code. | No test. |
| Lesson reader | Missing | `web/src/app/page.tsx` reads extracted source pages, not generated lessons. | Page-reader tests ran; lesson behavior is unverified/missing. |
| Recall questions | Partial | `src/learnbook/api/schemas.py::PracticeQuestion`, `src/learnbook/api/summary.py`, `web/src/app/page.tsx::GuidePanel` | Mock summary/schema test ran with no practice items. Recall scoring, answer checking, and mastery gating are missing and unverified. |
| Saved passages | Missing | No passage table, API route, or UI. | No test. |
| Notes | Missing | No notes model, persistence, route, or UI. | No test. |
| Topic status (new/learning/understood/review) | Missing | No topic-status persistence or controls. | No test. |
| Progress visual | Missing | `web/src/app/page.tsx` has a static product workflow strip only; no book-map status tree, heatmap, or mastered-core percentage. | No test. |
| Delete data | Partial | `src/learnbook/api/main.py` individual/library delete routes; `web/src/app/page.tsx` delete controls; Supabase cascade in migration | Fake-Supabase delete test ran. Real Storage/Postgres deletion is unverified; usage-quota rows remain for the account, and account deletion is not implemented. |

The 42 passing tests are offline/unit/API tests with a fake Supabase boundary. They do not establish live Supabase isolation, actual Gemini quality, or whole-book coverage on a book you know well.

## Product Spec Audit (2026-10-13)

| Capability | Status | Implementing file(s) | Test coverage / verification |
| --- | --- | --- | --- |
| Book map generation | Partial | `src/learnbook/api/summary.py`, `src/learnbook/api/schemas.py`, `web/src/app/page.tsx` | Mock schema/citation path in `tests/test_api.py` was run. Current output is a flat overview/ideas/frameworks/practice guide, not hierarchical topics/subtopics with ranking and study time. Real Gemini generation is unverified. |
| Whole-book coverage (chunking) | Partial | `src/learnbook/api/summary.py::_page_chunks`, `generate_book_summary` | Synthetic marker/split tests in `tests/test_api.py` were run. Strategy chunks page text at 24k chars, summarizes each chunk, then merges chunk notes; coherent coverage of a real book is unverified. |
| Page-reference validation | Partial | `src/learnbook/api/summary.py::generate_book_summary`, `src/learnbook/api/schemas.py` | Valid page citation test in `tests/test_api.py` was run. Range check rejects pages outside 1..page_count; invalid-citation rejection has no direct test, and semantic support for a citation is unverified. |
| Preferences screen | Missing | No preferences screen/model exists in `web/src/app/page.tsx` or API routes. | No test. |
| Learning-path builder | Missing | No path selection, prerequisite ordering, or optional-topic model exists. | No test. |
| Lesson reader | Missing | `web/src/app/page.tsx` reads extracted source pages only; no generated lesson entity or route. | Source page browsing tests ran; lesson behavior is missing/unverified. |
| Recall questions | Partial | `src/learnbook/api/schemas.py::PracticeQuestion`, `src/learnbook/api/summary.py`, `web/src/app/page.tsx::GuidePanel` | Mock guide schema test ran with empty practice items. Practice prompts can be generated, but there is no answer capture, grading, or mastery gate; real questions are unverified. |
| Saved passages | Missing | No passage/highlight table, API route, or UI. | No test. |
| Notes | Missing | No notes table, API route, or UI. | No test. |
| Topic status (new/learning/understood/review) | Missing | No per-topic status model or route. | No test. |
| Progress visual | Missing | `web/src/app/page.tsx` has a static product workflow strip, not a book-map tree/heatmap or mastery percentage. | No test. |
| Delete data | Partial | Individual and library delete routes in `src/learnbook/api/main.py`; controls in `web/src/app/page.tsx`; cascades in the Supabase migration. | Fake-Supabase deletion tests in `tests/test_api.py` were run. Real object/DB deletion is unverified; quota audit rows remain until account deletion, and account deletion itself is not implemented. |

### Audit Smoke-Test Readiness


## Next task

Review public launch choices: AGPL-3.0 licensing, the copyright/takedown contact, real account-recovery and abuse-report processes, and transactional storage quotas before enabling public traffic.