# LearnBook

LearnBook is a foundation for a personal PDF learning app that will turn book PDFs into source-cited learning guides. The current milestone establishes project configuration and tests; PDF processing, AI integration, and a user interface are not implemented yet.

## Windows setup

Install Git, Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/getting-started/installation/). From PowerShell, clone the repository and install its locked dependencies:

```powershell
git clone https://github.com/MohdSiddiq12/Personal-Learning-System.git
Set-Location Personal-Learning-System
uv sync
Copy-Item .env.example .env
```

Edit `.env` only when you need to override the documented local settings. No API keys are required for the current milestone.

## Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
