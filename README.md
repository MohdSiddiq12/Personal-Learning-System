# LearnBook

LearnBook is a book-to-learning workspace. It stores your PDF in a private account library, builds a page-cited map and time-based learning path, and generates lessons with the server-side Groq provider after you consent. It also saves progress, notes, and page passages.

## Windows setup

Install Git, Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/getting-started/installation/). From PowerShell, clone the repository and install its locked dependencies:

```powershell
git clone https://github.com/MohdSiddiq12/Personal-Learning-System.git
Set-Location Personal-Learning-System
uv sync
Copy-Item .env.example .env
```

Edit `.env` with your Supabase server settings and a Groq API key/model to use generation locally. Keep secrets in the server `.env` only and never put them in frontend variables.

## Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm run test --prefix web
npm run lint --prefix web
npm run build --prefix web
npm audit --prefix web
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

To configure local Supabase-backed development, set values in `.env` and `web/.env.local` using their examples, apply the SQL migrations in order as documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), then run the API and frontend in separate terminals:

```powershell
uv run uvicorn learnbook.api.main:app --reload --host 127.0.0.1 --port 8000
npm run dev --prefix web
```

Open `http://localhost:3000`. The API health endpoint is `http://localhost:8000/health`. Generate local prototype samples with `uv run python scripts/make_sample_pdf.py`; run the existing Streamlit prototype with `uv run streamlit run src/learnbook/app/main.py`.
