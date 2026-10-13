# Testing

## Automated test layers

- Unit tests in `tests/test_view_models.py` exercise summaries, page previews, page-marked export, and literal case-insensitive search without Streamlit.
- App tests in `tests/test_app.py` use Streamlit AppTest to upload generated valid, corrupt, and encrypted PDFs and verify the visible result.
- Browser tests in `tests/test_app_e2e.py` are marked `e2e`. They exercise the running local site and save success/error screenshots under `data/screenshots/`.
- Frontend component tests use Vitest, Testing Library, and jsdom. They cover time presets and validation, consent gating, path ordering and labels, shelf progress, self-reported progress, source-page filtering, recall-answer reveal, completion requests, same-day next-topic and session-done states, cached sequential prefetch, job recovery/retry/error states, and map-load errors.

The default suite stays fast and local:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm run test --prefix web
npm run lint --prefix web
npm run build --prefix web
npm audit --prefix web
```

The frontend component suite is local and offline after `npm install --prefix web`. It does not add production dependencies.

The browser test requires Chromium once (approximately 250-300 MB for the browser, headless shell, and support files). Start the app in one terminal, then run the marked test in another:

```powershell
uv run playwright install chromium
uv run python scripts/make_sample_pdf.py
uv run streamlit run src/learnbook/app/main.py
uv run pytest -m e2e
```

To use an existing Chrome installation instead, set `LEARNBOOK_CHROMIUM_EXECUTABLE` to its executable path before `uv run pytest -m e2e`; this avoids the browser download.

The app binds to `localhost` on port 8501. The generated PDFs and screenshots are ignored under `data/`.

## Manual test checklist

- Upload a PDF you trust and confirm its displayed page count matches your PDF viewer.
- Spot-check pages 1, a middle page, and the final page against the PDF viewer.
- Upload a scanned/image-only PDF and confirm the OCR warning appears.
- Try a non-PDF or a text file renamed with a `.pdf` extension; confirm it is rejected without a traceback.
- Upload the same PDF again in the same session and confirm the duplicate message appears.
- Open a lesson and confirm its source panel only contains the cited pages.
- Refresh the browser and confirm your account session and library return without clearing saved server data.

## Manual Task 8 product test (12 steps)

1. Start FastAPI and Next.js using the local development instructions above, and sign in.
2. Upload a text PDF and check the book appears on the shelf. Upload a scanned PDF and confirm learning is stopped with an OCR message.
3. On a text PDF, choose **Customize my learning path** and check that no generation starts before consent.
4. Choose each preset and test custom values 4, 5, 15, 180, 181, 15.5, and empty. Invalid values must explain what to correct.
5. Check consent and start map generation. Confirm the step label and progress bar update.
6. Refresh while a map job is active. Confirm the active job resumes polling. For a failed job, confirm Retry appears; for exhausted capacity, confirm the tomorrow message.
7. Check the map tree shows parent/child nesting, kind, importance, minutes, and text status labels.
8. Build the path. Confirm day totals, condensed and weak-support labels, optional bonus topics, and the first incomplete session button.
9. Open a lesson. Confirm generation asks for consent, cached lessons load without another job, source panels show only cited pages, and recall answers stay hidden until requested.
10. Save a note and a passage from a cited page. Use **Got it** and **Need review** and confirm status and progress update.
11. Change daily minutes and rebuild. Confirm completed items remain marked done and unfinished items are rescheduled.
12. Check Path, Learned, Progress, and shelf cards on a narrow mobile viewport. Confirm keyboard focus, labels, loading/errors, and text labels remain understandable without color.
