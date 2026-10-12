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

## Next task

Phase 3: Persist extracted documents and page-level source records (SQLite-first planned).