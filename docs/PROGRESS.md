# Progress

## Phase 1: Project foundation

### Completed

- Added the `learnbook` Python package scaffold, environment-backed settings, and basic logging configuration.
- Declared runtime and development dependencies and configured uv, pytest, and Ruff.
- Added smoke tests, setup documentation, architecture guidance, and technical decision records.
- Added environment, generated-data, PDF, and tooling-cache ignore rules.

### Validation

Validation run on Windows with uv-selected CPython 3.13.5:

- `uv sync`: succeeded; 18 packages resolved and the project installed.
- `uv run pytest`: 2 tests passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed; 9 files already formatted.

## Next task

Phase 2: PDF upload and text extraction with page numbers. Treat all uploaded document content as untrusted input.