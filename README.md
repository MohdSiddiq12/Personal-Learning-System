# LearnBook

LearnBook is a local-first PDF learning demo that extracts text page by page so readers can browse and search their books. Uploaded files are processed in memory on this machine; the demo has no database, AI integration, or OCR.

## Windows setup

Install Git, Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/getting-started/installation/). From PowerShell, clone the repository and install its locked dependencies:

```powershell
git clone https://github.com/MohdSiddiq12/Personal-Learning-System.git
Set-Location Personal-Learning-System
uv sync
Copy-Item .env.example .env
```

Edit `.env` only when you need to override local settings. No API keys are required.

## Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The default pytest run excludes browser tests and stays local and fast. Browser tests use Playwright. Installing its Chromium browser and headless shell downloads approximately 250-300 MB:

```powershell
uv run playwright install chromium
uv run pytest -m e2e
```

If Chrome is already installed, the e2e test can use it without downloading a browser:

```powershell
$env:LEARNBOOK_CHROMIUM_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
uv run pytest -m e2e
```

## Generate samples and run the app

```powershell
uv run python scripts/make_sample_pdf.py
uv run streamlit run src/learnbook/app/main.py
```

The sample PDFs are written under the ignored `data/` directory. Streamlit serves the app at `http://localhost:8501` by default.
