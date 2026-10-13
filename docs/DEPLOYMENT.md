# Public Deployment Plan

## UI options

| Option | Good fit | Trade-off |
| --- | --- | --- |
| Next.js + FastAPI (selected) | Account-based product, responsive reading, guided summaries, and a Python PDF core. | Two deployable services and separate frontend/backend configuration. |
| React + FastAPI | A client-only UI with the same Python API. | Routing, server rendering, and auth integration need more app code. |
| Keep Streamlit | Fast private demo and internal experiments. | Less control over public account UX, reader interactions, and product polish. |
| Gradio | A compact model demonstration. | Better for model inputs/outputs than a persistent multi-user book library. |

Next.js is a separate app under `web/`; the existing Streamlit app remains a local prototype. The selected public shape is Vercel for `web/`, Render (or a Docker-capable host) for FastAPI, and Supabase for Auth, Postgres, and private PDF Storage. Vercel can also host a Next.js Node server; Docker/Cloud Run/Fly are alternatives if one provider is preferred. These options are not configured with live credentials yet.

Shortform-inspired use cases are adapted as product patterns, not copied content: concise reading guides, comparisons of frameworks, recall/practice prompts, saved notes, and progress. The current implementation provides page-cited book maps, configurable paths, cached short lessons, source-page reading, recall self-checks, topic status, saved notes and passages, and a core-ideas progress view. Audio, recall grading, and mastery gating remain future work. Mastery must be tied to successful recall, not lesson opens.

## Supabase setup

1. Create a Supabase project and configure Auth email/password plus email confirmation. Before a public launch, configure a real SMTP sender, site URL, and redirect URLs for localhost and the production frontend.
2. Apply the migrations in order in the Supabase SQL editor or with the Supabase CLI: [public books](../supabase/migrations/202610130001_public_books.sql), [learning path](../supabase/migrations/202610140001_learning_path.sql), [lessons](../supabase/migrations/202610150001_lessons.sql), [generation jobs](../supabase/migrations/202610160001_generation_jobs.sql), and [digest and path progress](../supabase/migrations/202610160002_digest_path_progress.sql). They create owner-scoped books, maps, learning paths, lessons, resumable generation jobs, chunk results, token usage records, digest/outline metadata, and RLS policies.
3. Set API secrets on the backend only: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GROQ_API_KEY`, and `GROQ_MODEL`. The service-role and Groq keys must never be placed in `web/.env.local`, a `NEXT_PUBLIC_*` variable, source control, or browser code.
4. Set frontend values in `web/.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`, and `NEXT_PUBLIC_TAKEDOWN_EMAIL`. The publishable/anon key is designed for browser use; RLS is the access boundary.
5. Set backend `FRONTEND_ORIGINS` to the exact comma-separated frontend origins. Keep localhost in development and the deployed domain in production.

PDFs are saved under a private bucket path scoped to the authenticated Supabase user. API retrieval uses a five-minute signed URL after ownership verification. Extracted pages, generated guides, topics, lessons, progress, preferences, paths, notes, and highlights are stored in Postgres; deleting a book cascades its related rows and removes its storage object. The API verifies the Supabase access token before any service-role request and derives the owner ID from that verified user, never from a caller-supplied owner field.

The current Supabase pricing page (checked 2026-10-13) lists Free with 500 MB database, 1 GB file storage, and 50 MB maximum upload; free projects can pause after a week of inactivity. Quotas and prices can change. Defaults are 50 MB per PDF, 500 pages per hosted book, a 30-second parser process timeout, two concurrent parser processes per API instance, 3 million extracted characters per book, 10 valid uploads per user per day, 20 books and 100 MB retained PDFs per account. Generation job creation atomically checks the per-user daily map/lesson limit, one active job per user and kind, and remaining global daily token budget. The owner funds the shared Groq organization account, so the daily budget, per-minute pacing, request caps, and user quotas are required cost controls.

## Model privacy and cost

Map and lesson generation requires explicit user consent before sending relevant book text to Groq. The owner configures `GROQ_API_KEY` and `GROQ_MODEL` on the backend only. User-facing consent must explain that relevant source text goes to the provider. The project owner must read Groq's current data-retention and usage terms before launch and update the terms page accordingly. Do not promise provider retention or training behavior without verifying the owner's applicable account terms.

Book maps run as resumable background jobs. Completed per-chunk candidate outputs and actual provider usage are stored after each successful chunk. A server restart interrupts the in-process worker; after a five-minute stale heartbeat, the user can retry and completed chunks are reused. The token bucket and single-flight lock are process-local, so deploy a single API instance until a distributed queue and limiter exist. The database job creation function uses an advisory lock for atomic daily-budget and active-job checks.

## Local development

In PowerShell, from the repository root:

```powershell
uv sync
Copy-Item .env.example .env
Copy-Item web/.env.example web/.env.local
npm install --prefix web
```

Set Supabase values and `GROQ_API_KEY` plus `GROQ_MODEL` in root `.env`, set public Supabase and API values in `web/.env.local`, apply all migrations in order, and allow `http://localhost:3000` in Supabase Auth redirect URLs. Start the API and UI in separate terminals:

```powershell
uv run uvicorn learnbook.api.main:app --host 127.0.0.1 --port 8000
npm run dev --prefix web
```

The UI runs at `http://localhost:3000`; API health is at `http://127.0.0.1:8000/health`. The local map-generation worker runs inside the API process. A restart may interrupt a job; retry resumes saved chunks.

## Deploy

- **Frontend:** import the repository in Vercel and set the project root to `web`. Add the four `NEXT_PUBLIC_*` values from `web/.env.example`.
- **API:** deploy the root [`Dockerfile`](../Dockerfile) on Render or another Docker host. Set server environment names from `.env.example`, including `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_TIMEOUT_SECONDS`, `GROQ_MAX_RETRIES`, `GROQ_MAX_REQUEST_TOKENS`, `GROQ_TPM_LIMIT`, `GROQ_DAILY_TOKEN_BUDGET`, `GROQ_MAX_TOTAL_WAIT_SECONDS`, `GROQ_JSON_MODE_SUPPORTED`, `MAX_BOOKS_PER_USER_PER_DAY`, `MAX_LESSONS_PER_USER_PER_DAY`, and the upload/storage limits. Set `ENVIRONMENT` to production and `FRONTEND_ORIGINS` to the deployed Vercel origin. Production startup requires the Groq key and model. `render.yaml` is a starter blueprint; enter secrets in the host dashboard.
- **Database and files:** apply the migration to the production Supabase project, configure Auth redirect URLs, and confirm the bucket is private and RLS policies are enabled.
- **Before public traffic:** set the real takedown contact, review the terms/privacy copy with counsel, select a project license, confirm PyMuPDF's AGPL obligations, and test account isolation/deletion using at least two real accounts.

## Alternatives and launch gaps

The Next.js + FastAPI route is selected for this build. Streamlit Community Cloud remains useful for the existing demo but is not the recommended public multi-user UI. React/Vite + FastAPI is a credible alternative if static hosting is preferred; Gradio is suitable for an AI prototype, not the target account/library product.

No Supabase project or real credentials were available here, so real sign-in, storage, RLS, signed retrieval, deletion, and Groq calls are not live-verified. Free-tier limits and account terms can change. The current deployment starter also does not yet include a production account-recovery flow, a monitored abuse/report queue, formal terms reviewed by counsel, or hardened container memory/CPU limits. Do not treat this scaffold as a public launch approval.

## Official references

- [Shortform product site](https://www.shortform.com/): product-category inspiration only; no summaries or copy are reused.
- [Supabase pricing](https://supabase.com/pricing): plan/storage quotas and inactivity behavior; recheck before launch.
- [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control): private bucket RLS policies.
- [Supabase standard uploads](https://supabase.com/docs/guides/storage/uploads/standard-uploads): upload sizes and resumable upload guidance.
- [Next.js deployment](https://nextjs.org/docs/app/getting-started/deploying), [FastAPI deployment](https://fastapi.tiangolo.com/deployment/), and [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud): hosting references.
