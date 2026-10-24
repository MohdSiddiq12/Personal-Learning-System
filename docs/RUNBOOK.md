# LearnBook Runbook (Windows PowerShell)

## Quick Start

### Prerequisites
- Windows with PowerShell
- Python 3.12 (managed by uv)
- Node.js 20+ (for Next.js frontend)
- uv (`pip install uv`)
- Git

### Clone and Setup
```powershell
git clone <repo-url>
cd D:\Learn-Books

# Backend
uv sync

# Frontend
npm install --prefix web
```

### Environment Files
Copy example files and fill in real values:
```powershell
copy .env.example .env
copy web\.env.example web\.env.local
```

Edit `.env` with your Supabase and Groq credentials.
Edit `web\.env.local` with your Supabase public credentials.

**Required in `.env`:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anon (publishable) key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (backend only!)
- `GROQ_API_KEY` - Groq API key
- `GROQ_MODEL` - Model name (e.g., `openai/gpt-oss-120b`)

**Required in `web\.env.local`:**
- `NEXT_PUBLIC_SUPABASE_URL` - Same as `SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Same as `SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` - Backend URL (local: `http://127.0.0.1:8000`)
- `NEXT_PUBLIC_TAKEDOWN_EMAIL` - Copyright contact email

---

## Running Locally

### Terminal 1: Backend API
```powershell
cd D:\Learn-Books
uv run uvicorn learnbook.api.main:app --host 127.0.0.1 --port 8000
```
Health check: `http://127.0.0.1:8000/health` → `{"status":"ok"}`

### Terminal 2: Frontend
```powershell
cd D:\Learn-Books
npm run dev --prefix web
```
Frontend: `http://localhost:3000`

### Terminal 3 (optional): Streamlit Prototype
```powershell
cd D:\Learn-Books
uv run streamlit run src/learnbook/app/main.py
```
Prototype: `http://localhost:8501`

---

## Running Tests

### Python Tests (offline, no live services)
```powershell
cd D:\Learn-Books
uv run pytest                    # 81 passed, 1 deselected
uv run pytest -m e2e             # Browser test, needs LEARNBOOK_CHROMIUM_EXECUTABLE
uv run ruff check .
uv run ruff format --check .
uv sync --locked
```

### Frontend Tests
```powershell
cd D:\Learn-Books
npm run lint --prefix web
npm test --prefix web
npm run build --prefix web
npm audit --prefix web
```

### Live Verification Script (opt-in)
```powershell
cd D:\Learn-Books
$env:LIVE_E2E=1
uv run python scripts/verify_live.py
```

### Live E2E Playwright Test (opt-in)
```powershell
cd D:\Learn-Books
$env:LIVE_E2E=1
uv run pytest -m e2e tests/test_live_e2e.py
```

---

## Supabase Free Project: Wake Up a Paused Project

The Supabase free tier pauses projects after ~1 week of inactivity.

1. Go to https://supabase.com/dashboard
2. Select your project
3. If status shows "Paused", click "Resume project"
4. Wait 30-60 seconds for database to become available
5. Verify: `curl -H "apikey: $SUPABASE_ANON_KEY" $SUPABASE_URL/rest/v1/`

**Note**: First request after resume will be slow (10-30s cold start).

---

## Backup (Task 8)

### Weekly Database Backup
```powershell
# Get connection string from Supabase dashboard → Settings → Database
# Format: postgresql://postgres:[password]@[host]:5432/postgres
$env:SUPABASE_DB_URL="postgresql://postgres:PASSWORD@HOST:5432/postgres"

# Run backup
$date = Get-Date -Format "yyyyMMdd_HHmmss"
pg_dump $env:SUPABASE_DB_URL --no-owner --no-privileges > "backups/learnbook_$date.sql"

# Compress
Compress-Archive "backups/learnbook_$date.sql" "backups/learnbook_$date.zip"
Remove-Item "backups/learnbook_$date.sql"
```

### Export Learning Data (JSONL)
```powershell
# Using backend API (requires auth token)
$token = "YOUR_JWT_TOKEN"
curl -H "Authorization: Bearer $token" http://127.0.0.1:8000/api/export/learning-data > "backups/learning_data_$date.jsonl"
```

### Storage
Store backups in:
- Local encrypted drive
- Or: OneDrive/Google Drive with client-side encryption
- Or: AWS S3 Glacier / Backblaze B2 (costs pennies/month)

### Restore
```powershell
# Database
pg_restore -d $env:SUPABASE_DB_URL "backups/learnbook_20261024_120000.sql"

# Learning data: POST each JSONL line to appropriate endpoints
```

**If pg_dump not installed:**
```powershell
# Install PostgreSQL client tools
winget install PostgreSQL.PostgreSQL
# Or download from: https://www.postgresql.org/download/windows/
```

---

## Live Checks Checklist

Run `scripts/verify_live.py` and verify all checks PASS:

- [ ] Required env vars present
- [ ] Supabase reachable and auth works
- [ ] Backend accepts valid JWT, rejects invalid/expired
- [ ] Migration tables exist, RLS enabled
- [ ] Storage bucket private (unauthenticated fetch fails)
- [ ] Groq call works: latency, tokens, model name, rate-limit headers recorded

---

## Single-User Guard

Set `ALLOWED_EMAILS` in `.env` (comma-separated):
```powershell
ALLOWED_EMAILS=your@email.com
```

Then **disable public sign-ups in Supabase Dashboard**:
1. Go to Authentication → Providers → Email
2. Turn OFF "Enable email signups"
3. Save

---

## Secrets Safety

**Never commit:**
- `.env`, `.env.*`, `web/.env.local`
- Any file with real API keys

**Safe to commit:**
- `.env.example`, `web/.env.example`
- `docs/` files

**To check for leaks before commit:**
```powershell
git diff --cached | grep -i "sk_\|gsk_\|supabase.*key\|password"
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `uv` not found | `pip install uv` |
| `uv sync` fails | Check Python 3.12 in `.python-version` |
| CORS error | Add frontend origin to `FRONTEND_ORIGINS` in `.env` |
| Supabase auth fails | Check `SUPABASE_URL` and keys match dashboard |
| Groq 429 rate limit | Wait, check `GROQ_TPM_LIMIT` and `GROQ_DAILY_TOKEN_BUDGET` |
| Next.js build fails | Run `next upgrade --agent=security` in `web/` |
| Playwright test fails | Set `LEARNBOOK_CHROMIUM_EXECUTABLE` to Chrome path |

---

## Useful Commands

```powershell
# Check running processes on ports
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# Kill process on port
taskkill /PID <PID> /F

# View backend logs
Get-Content .\logs\api.log -Tail 50 -Wait

# Check Supabase project status
curl -H "apikey: $env:SUPABASE_ANON_KEY" $env:SUPABASE_URL/rest/v1/
```