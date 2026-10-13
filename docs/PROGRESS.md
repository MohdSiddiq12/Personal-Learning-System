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

## Task 6: Backend learning foundations (2026-10-13)

**Status: Implemented locally; Supabase migration and live provider remain unverified**

### Completed

- Added a new migration for topics, topic progress, learning preferences, paths and path items, highlights, and notes. Each table has owner RLS, user/book indexes, and book deletion cascades. Composite foreign keys keep topic, path, book, and owner references aligned.
- Expanded BYOK Gemini generation into chunk candidate extraction and whole-book hierarchy synthesis. Pydantic validates map structure and page citations; invalid citations are rejected. The existing consent gate and untrusted-book-text instruction remain in place.
- Added deterministic core path scheduling, plus authenticated owner-filtered map, path, preferences, topic status, highlight, and note routes with request length limits.
- Kept the frontend unchanged. Preferences, lessons, recall grading, saved passage UI, and progress visualization remain for Task 7 and Task 8.
- Removed the duplicate product audit table and empty smoke-test heading.

### Validation

- `uv run pytest`: 52 passed, 1 browser test deselected after Task 6 changes.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 37 Python files formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked. No dependencies added.
- Initial frontend checks: `npm install --prefix web`, lint and build passed; `npm audit --prefix web` found 0 vulnerabilities. Frontend files were not changed.
- Baseline browser test failed because Playwright Chromium was not installed and `LEARNBOOK_CHROMIUM_EXECUTABLE` was unset.

### Decisions, limitations, and unverified items

- The core scheduler keeps over-budget topics in the path as optional items at the end. It does not split one topic across multiple lessons.
- Supabase policies and cascade behavior were checked by parsing the migration in offline tests. Applying the migration, real RLS isolation, deletion against a live project, and API behavior with live Supabase remain unverified.
- Real Gemini map quality, coverage, semantic citation support, and provider cost remain unverified. Page references are range-checked, not semantically verified.
- No new dependencies were added. No secrets were printed or committed.

### Baseline handover verification

- Python suite: 42 passed, 1 deselected. Ruff and format checks passed; locked sync passed.
- Frontend install, lint, production build, and audit passed; audit reported 0 vulnerabilities.
- The e2e check was not available: its configured system Chrome was not exposed in this shell, and the Playwright-managed browser is absent.
- Repo mismatch: `Agents.md` (capital A) is the only untracked file. It was preserved and not included in the code commit.

## Next task

Build the frontend preferences, path, lesson, note/highlight, and progress flows, then add UI-level coverage.

## Task 7 backend checkpoint (2026-10-13)

**Status: Lessons API and storage are implemented locally; frontend work is in progress**

- Added `supabase/migrations/202610150001_lessons.sql` with owner RLS, a unique user/topic cache, and cascading topic/book foreign keys.
- Added validated lesson generation from cited pages plus a one-page neighbor margin. Source input is capped at 30,000 characters. Generation requires explicit consent, a per-request BYOK key, and an existing AI quota reservation.
- Added authenticated GET and POST lesson routes. Cached lessons return before consent or quota checks and do not call Gemini again.
- Tests cover 600-900 word length, exactly two recall answers, caching, topic ownership, quota rejection, selected pages, source cap, untrusted injected text, and migration RLS.
- Validation checkpoint: `uv run pytest tests/test_lessons.py tests/test_api.py` passed 23 tests; Ruff lint and format checks passed; `uv sync --locked` resolved 66 packages and checked 63 installed packages.
- Live Supabase migration/RLS and real Gemini lesson output remain unverified.

## Remaining launch work

Review AGPL-3.0 licensing, the copyright/takedown contact, account recovery and abuse reporting, transactional storage quotas, and public deployment requirements before enabling public traffic.
