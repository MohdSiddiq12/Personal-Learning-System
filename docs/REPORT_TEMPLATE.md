# BATCH-XX Report

## Batch
Batch number: XX

## Summary
One-paragraph summary of what was accomplished in this batch.

## Files Changed
List of files created or modified, with brief descriptions.

## Commands Run
Exact commands run with real output summaries (truncated if long).

### Python Checks
```
uv run pytest
```
Output: X passed, Y failed, Z deselected

```
uv run ruff check .
```
Output: [result]

```
uv run ruff format --check .
```
Output: [result]

```
uv sync --locked
```
Output: [result]

### Frontend Checks
```
npm run lint --prefix web
```
Output: [result]

```
npm test --prefix web
```
Output: [result]

```
npm run build --prefix web
```
Output: [result]

## Test Counts
- Python tests: X passed / Y failed / Z deselected
- Frontend tests: X passed / Y failed

## Decisions Made
Decisions that were not specified in the batch instructions, with reasons.

## Known Limitations
Any limitations or issues discovered.

## Unverified
Anything not run or not verified against live services.

## Pending
Out-of-scope ideas that came up during this batch.

## Recommended Next Task
Specific next batch or task recommendation.

## Git Diff Summary
Summary of `git diff --stat` showing only docs/ changes.