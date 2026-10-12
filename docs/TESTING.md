# Testing

## Automated test layers

- Unit tests in `tests/test_view_models.py` exercise summaries, page previews, page-marked export, and literal case-insensitive search without Streamlit.
- App tests in `tests/test_app.py` use Streamlit AppTest to upload generated valid, corrupt, and encrypted PDFs and verify the visible result.
- Browser tests in `tests/test_app_e2e.py` are marked `e2e`. They exercise the running local site and save success/error screenshots under `data/screenshots/`.

The default suite stays fast and local:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

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
- Download the extracted `.txt` file and confirm every page has an `=== Page N ===` separator.
- Refresh the browser and confirm session-only state is cleared; re-upload the PDF to browse it again.