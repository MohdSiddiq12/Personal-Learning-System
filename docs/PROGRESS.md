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
- Added opt-in legacy provider generation with a provider data-use consent gate and page citation validation.
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

No Supabase project, credentials, actual model provider key, or legal license decision is configured here. Real auth/storage/RLS and provider calls remain unverified. The terms page is explicitly a draft; configure the takedown contact and have counsel review it. No public deployment has been made.

## Task 6: Backend learning foundations (2026-10-13)

**Status: Implemented locally; Supabase migration and live provider remain unverified**

### Completed

- Added a new migration for topics, topic progress, learning preferences, paths and path items, highlights, and notes. Each table has owner RLS, user/book indexes, and book deletion cascades. Composite foreign keys keep topic, path, book, and owner references aligned.
- Expanded legacy provider generation into chunk candidate extraction and whole-book hierarchy synthesis. Pydantic validates map structure and page citations; invalid citations are rejected. The existing consent gate and untrusted-book-text instruction remain in place.
- Added deterministic core path scheduling, plus authenticated owner-filtered map, path, preferences, topic status, highlight, and note routes with request length limits.
- Kept the frontend unchanged during Task 6. Task 7 added the full preference, path, lesson, note/highlight, status, and progress views.
- Removed the duplicate product audit table and empty smoke-test heading.

### Validation

- `uv run pytest`: 52 passed, 1 browser test deselected after Task 6 changes.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 37 Python files formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked. No dependencies added.
- Initial frontend checks: `npm install --prefix web`, lint and build passed; `npm audit --prefix web` found 0 vulnerabilities. Frontend files were not changed.
- At Task 6 baseline, the browser test could not run because Playwright Chromium was absent and `LEARNBOOK_CHROMIUM_EXECUTABLE` was unset. Task 7 later ran it with system Chrome successfully.

### Decisions, limitations, and unverified items

- The core scheduler keeps over-budget topics in the path as optional items at the end. It does not split one topic across multiple lessons.
- Supabase policies and cascade behavior were checked by parsing the migration in offline tests. Applying the migration, real RLS isolation, deletion against a live project, and API behavior with live Supabase remain unverified.
- Real model provider map quality, coverage, semantic citation support, and provider cost remain unverified. Page references are range-checked, not semantically verified.
- No Task 6 dependencies were added. No secrets were printed or committed.

### Baseline handover verification

- Python suite: 42 passed, 1 deselected. Ruff and format checks passed; locked sync passed.
- Frontend install, lint, production build, and audit passed; audit reported 0 vulnerabilities.
- The configured system Chrome path was available during Task 7 and the existing Streamlit browser smoke test passed.
- Repo mismatch: `Agents.md` (capital A) is the only untracked file. It was preserved and not included in the code commit.

## Task 7 backend checkpoint (2026-10-13)

**Status: Complete locally; live Supabase and model provider behavior remain unverified**

### Files changed

- Backend: `src/learnbook/api/main.py`, `src/learnbook/api/schemas.py`, new `src/learnbook/api/lessons.py`, new `supabase/migrations/202610150001_lessons.sql`, and `tests/test_lessons.py` (later full suite: 60 passed, 1 deselected).
- Frontend: `web/src/components/learning/LearningLoop.tsx`, `web/src/components/learning/learningViews.tsx`, `web/src/components/learning/learning.test.tsx`, `web/src/test/setup.ts`, `web/vitest.config.mts`, `web/package.json`, `web/package-lock.json`, `web/src/app/page.tsx`, and `web/src/app/globals.css`.
- Documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/PROGRESS.md`, and `docs/TECH_DECISIONS.md`, and `docs/TESTING.md`.

- Added `supabase/migrations/202610150001_lessons.sql` with owner RLS, a unique user/topic cache, and cascading topic/book foreign keys.
- Added validated lesson generation from cited pages plus a one-page neighbor margin. Source input is capped at 30,000 characters. Generation requires explicit consent, a per-request user-supplied provider key key, and an existing AI quota reservation.
- Added authenticated GET and POST lesson routes. Cached lessons return before consent or quota checks and do not call model provider again.
- Tests cover 600-900 word length, exactly two recall answers, caching, topic ownership, quota rejection, selected pages, source cap, untrusted injected text, and migration RLS.
- Validation checkpoint: `uv run pytest tests/test_lessons.py tests/test_api.py` passed 24 tests; Ruff lint and format checks passed; `uv sync --locked` resolved 66 packages and checked 63 installed packages.
- Live Supabase migration/RLS and real model provider lesson output remain unverified.

### Frontend learning loop

- Added a book-map tree with status, kind, importance, and estimated minutes; saved preferences; ordered daily path with separate optional topics; lesson reading; source-page panel; answer reveal self-check; topic status buttons; topic notes; saved passages; and core progress visual.
- Core progress is labelled �understood� and counts importance 4 or 5 topics with the understood status. It is not a passed-recall mastery result; Task 8 still needs grading and mastery gating.
- Document and model text is rendered as React text. The user-supplied provider key key stays in component state, clears after generation and on topic/book changes, and is not written to browser storage.
- Added Vitest, Testing Library, and jsdom as dev-only dependencies. All are MIT licensed and have no usage fee. Vitest was selected for the Vite based component test runner; Jest is the main alternative.
- Component coverage: path order and optional grouping, core progress calculation and visual labels, hidden/revealed recall answers, and a learning-map error state.

### Task 7 acceptance results

- `uv run pytest`: 60 passed, 1 browser test deselected.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 39 Python files formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked.
- `npm run test --prefix web`: 4 component tests passed.
- `npm run lint --prefix web`: passed.
- `npm run build --prefix web`: passed; `/` and `/terms` prerendered.
- `npm audit --prefix web`: 0 vulnerabilities.
- `$env:LEARNBOOK_CHROMIUM_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'; uv run pytest -m e2e`: 1 passed, 59 deselected.

## Current capability gap table after Task 8

| Capability | Status | Remaining limitation |
| --- | --- | --- |
| Digest-based hierarchical book map | Implemented | Heuristic coverage and semantic citation support are unverified on known books. |
| Server-side Groq jobs and bounded quotas | Implemented | Live Groq behavior, durable workers, multi-instance operation, and real quota accounting are unverified. |
| Daily time preferences and path | Implemented | Live persistence and path rebuild behavior are unverified against Supabase. |
| Cited short lessons and source panel | Implemented | Real output quality, target duration, and source fidelity are unverified. |
| Recall self-check and topic completion | Implemented | Answers are not graded; understood remains self-reported. |
| Notes, saved passages, learned list, and shelf | Implemented | Live database behavior is unverified. |
| Progress visual | Implemented | Percentages are self-reported, not mastery results. |
| Public launch | Not ready | Apply migrations, two-account RLS check, verify Docker build, complete legal/contact decisions, harden limits, and deploy smoke test. |

## Remaining launch work

Review AGPL-3.0 licensing, the copyright/takedown contact, account recovery and abuse reporting, transactional storage quotas, and public deployment requirements before enabling public traffic.

**Recommended next task:** Task 9, hardening and launch preparation, including live Supabase RLS verification, account deletion, Docker build, container limits, and final privacy/legal review.

## Reliability fix (2026-10-14)

- Added a JSON service-info response at `/`; `/health` remains the deployment health check. Root and health probes returned HTTP 200 locally, and CORS returned the configured `http://localhost:3000` origin.
- The frontend now gives an actionable API-unreachable message and ends session initialization with a bounded error state instead of leaving the loading indicator indefinitely.
- Root cause confirmed from local configuration: the backend `.env` has no Supabase URL or keys, so auth-backed storage requests cannot work in this checkout until the owner configures the Supabase server credentials. The frontend API URL now uses the same explicit IPv4 loopback address as the documented backend bind, which requires the API process to be running locally.
- Added tests for the API root contract and frontend network failure message.
- Validation: Python 61 passed, 1 deselected; Ruff lint passed; Ruff format check passed (39 files); frontend lint passed; Vitest 5 passed; production build passed. Local `/` and `/health` plus local-origin CORS probes passed.
- Live Supabase signup, Storage upload, real account library load, and public deployment remain unverified because server-side Supabase credentials and deployed resources are not configured in this workspace.

## Task 8 Part 1 checkpoint: Groq and resumable generation jobs (2026-10-16)

### Files and behavior

- Replaced per-user model credentials with a server-side Groq-compatible provider. Added bounded retries and wait time, response parsing, request token estimates and caps, a process token bucket, one in-flight provider request per process, JSON mode configuration, and usage capture. No model key or document text is logged or returned.
- Book-map generation now runs as an owner-scoped background job. The new migration adds generation jobs, resumable chunk results, an LLM usage ledger, owner RLS, atomic budget and daily job admission, and an atomic active-job constraint. Completed chunks are reused after interruption.
- Added map job creation, status, active-job, and retry endpoints. Map generation and lesson generation require an explicit provider data-use consent. The existing lesson endpoint now uses the server provider.
- Updated the frontend map and lesson consent flows to remove the user API key and show job progress. The frontend continues polling only within the current session; restart recovery and the rest of the pivot flow are Part 3.
- Updated configuration examples, Render settings, privacy, deployment, architecture, decisions, README, terms, and this handover.

### Validation

- `uv run pytest`: 77 passed, 1 deselected.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 45 Python files already formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked. No new dependencies were added; `httpx` was already installed and locked.
- Targeted provider, generation-resume, job-route, lesson, API, and configuration tests: 44 passed.
- Real Groq calls, deployed job execution, live Supabase migration/RLS/RPC behavior, and production quota behavior remain unverified.

### Decisions and limitations

- Groq JSON response mode defaults off because supported models vary; prompts still request JSON and responses are schema validated with one repair attempt.
- Job workers currently run as FastAPI background tasks, so production deployment must keep a single backend instance as documented. Heartbeats, saved chunks, and retry resume interrupted work, but durable cross-instance queues and transactional topic-tree replacement are deferred.
- Documented Generation Jobs and Groq limits are configurable. The process token bucket is local to each backend process; the database budget and admission functions enforce the shared daily job and token accounting.

## Task 8 Part 2 checkpoint: digest, paths, lessons, and progress (2026-10-16)

### Files and behavior

- Added `core/understanding/digest.py`, a deterministic extractive digest with term rarity, paragraph and section position, cue phrases, heading proximity, per-section size bounds, page markers, and coverage statistics. PDF ingestion captures outline sections; digest fallback detects headings or uses ten-page windows.
- Map generation consumes digest passages, merges candidates by normalized title and key-term overlap, caps the compact map, applies deterministic importance and 5/10-minute estimates, drops invalid page references, and labels lexical support `ok` or `weak`.
- Learning preferences now enforce daily minutes between 5 and 180. Paths place parents first, core ideas before low-importance optional topics, fit daily budgets, condense longer topics, and omit completed topics when rebuilt. Path responses group items by day and report allocated minutes.
- Added lesson targets, per-target lesson caching, and a lesson job endpoint. Added path-item completion, per-book progress, shelf, and learned-topic endpoints.
- Added migration `202610160002_digest_path_progress.sql` for topic terms/support, path metadata, lesson target uniqueness, daily digest storage, and PDF outline metadata. New tables have owner RLS.

### Current validation

- Focused digest, scheduler, lesson, and map-resume tests: 19 passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 48 Python files formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked.
- `uv run pytest`: 80 passed, 1 browser test deselected.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 48 Python files already formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked. No dependencies added.

### Limitations and unverified behavior

- Digest coverage and citation ranges are deterministic, but semantic support and map quality on known books are not evaluated yet.
- Lesson jobs use the in-process FastAPI background worker; durable queue behavior and live Groq/Supabase quotas remain unverified.
- Rebuilding a path now keeps completed path items with their original day, position, allocation, and completion timestamp, then schedules only unfinished topics. Live migration application, RLS and RPC behavior remain unverified.

## Task 8 Part 3 and final verification

### Frontend flow

- Files changed in this checkpoint: `web/src/app/page.tsx`, `web/src/app/layout.tsx`, `web/src/app/globals.css`, `web/src/components/learning/LearningLoop.tsx`, `web/src/components/learning/learningViews.tsx`, new `web/src/components/learning/ShelfBookCard.tsx`, and `web/src/components/learning/learning.test.tsx`.
- Replaced the page browser, page search, page picker, and text export with the learning flow. The lesson source panel only renders pages cited by the active topic.
- Added the mode choice, daily-time presets and validated custom time, consent gate, resumable map-job progress and retry states, map tree, ordered path, bonus section, lesson reader, hidden-answer self-check, notes, cited-page passage saving, status and completion actions, learned/progress tabs, and shelf progress cards.
- Shelf cards now include an accessible path progress bar, percentage, core-ideas count, continue day/time, and book-selection action. UI copy avoids em dashes. Interactive book content stays rendered as text.
- Added component tests for preset/custom time selection, consent gating, shelf progress, path order and badges, progress calculation, answer reveal, cited source filtering, completion API calls, same-day next-topic and session-done states, cached sequential prefetch, map-job recovery/retry and budget errors, and map-load errors.
- Added `scripts/smoke_groq.py`. The configured backend key was present, but `GROQ_MODEL` was not configured. The script was run and safely reported that no request was sent. No provider key or book text was printed or transmitted.
- Updated `src/learnbook/api/main.py` and `tests/test_api.py`: map responses now include the persisted overview, cached lesson reads select the requested 5/10-minute target, shelf reads handle books without a path, and a path rebuild preserves completed items. A focused regression test verifies the saved completion fields.
- Updated `Agents.md`, `docs/DEPLOYMENT.md`, `docs/PROGRESS.md`, `docs/TECH_DECISIONS.md`, and `docs/TESTING.md` to match the provider, limits, flow, checks, and launch gaps.

### Final checks

- `uv run pytest`: 81 passed, 1 deselected.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 49 Python files already formatted.
- `uv sync --locked`: passed; 66 packages resolved and 63 checked. No runtime dependencies were added.
- `npm run lint --prefix web`: passed.
- `npm run test --prefix web`: 16 tests passed across 2 files.
- `npm run build --prefix web`: passed; `/`, `/_not-found`, and `/terms` built, with `/` and `/terms` statically prerendered.
- `npm audit --prefix web`: 0 vulnerabilities.
- Browser smoke test: run with installed Chrome and the local Streamlit prototype. It failed because the prototype remained on Streamlit's “Running...” screen, so the expected “LearnBook” heading never appeared. The public Next.js flow is covered by Vitest and the production build, but browser-level testing remains unverified.

### Self-review and limits

- Tracked-source scans were clear for removed per-user model credentials, browser storage, HTML injection, backend-only credentials in frontend code, em dashes in frontend source, and secret-shaped strings.
- Live Supabase auth, storage, migrations, RLS, and RPC behavior remain unverified. Live Groq behavior is unverified because no model was configured. Public deployment and Docker build remain unverified.
- The background worker and token pacing are process-local. Keep a single backend instance until a durable queue and distributed limiter are added.

**Recommended next task:** Task 9, hardening and launch preparation, including the browser-test investigation, live Supabase isolation checks, account deletion, Docker build, and launch/privacy review.
