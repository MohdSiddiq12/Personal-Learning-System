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

OCR and a timeout for pathological PDFs are not implemented; only upload-size and page-count limits are enforced.

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

No upload is written to disk by the app. OCR and a timeout for pathological PDFs remain unimplemented.

## Next task

Phase 4: Persist extracted documents and page-level source records (SQLite-first planned).