# LearnBook

LearnBook is a book-to-learning workspace. It stores your PDF in a private account library, extracts page-cited text, and can generate an original study guide with cited ideas, frameworks, and practice prompts after you explicitly consent and provide a Gemini API key.

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

## Public app architecture

The production direction is Next.js UI + FastAPI/PyMuPDF API + Supabase Auth, Postgres, and private Storage. Streamlit remains available as the local prototype. Frontend and API deployment options, Supabase setup, quotas, privacy limits, and unverified launch steps are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

To configure local Supabase-backed development, set values in `.env` and `web/.env.local` using their examples, apply the SQL migration, then run the API and frontend in separate terminals:

```powershell
uv run uvicorn learnbook.api.main:app --reload --host 127.0.0.1 --port 8000
npm run dev --prefix web
```

Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/health`. Generate local prototype samples with `uv run python scripts/make_sample_pdf.py`; run the existing Streamlit prototype with `uv run streamlit run src/learnbook/app/main.py`.
