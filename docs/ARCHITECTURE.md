# Architecture

The deployment has two UI paths. Streamlit remains a local prototype; the public app is:

```text
Browser -> Next.js -> FastAPI -> core
						 |-> Supabase Auth / Postgres / private Storage
						 |-> Groq chat completions (server-side key, consented background jobs)
```

The Next.js client uses Supabase Auth for sessions and sends the access token to FastAPI. FastAPI verifies it with Supabase Auth, derives the owner ID from the verified response, and performs explicit owner-filtered repository operations. Its service-role and Groq keys are server-only. Core owns extraction and document rules; core must not import either UI or API code. Book-map generation runs as a resumable background job. Provider usage is stored in the daily ledger and job chunks are persisted after each completed extraction batch.

PDF ingestion lives in `learnbook.core.ingestion`. Its flow is:

```text
Path or bytes -> size/header checks -> PyMuPDF validation -> ordered page text + metadata/hash
```

The ingestion module is core logic: it has no UI, database, provider, network, OCR, or rendering dependency. Its results keep each page and its 1-based page number separate so later layers can cite source locations.

The local prototype lives in learnbook.app; pure display transformations live in view_models.py. Hosted routes live in learnbook.api. Uploaded PDF bytes are parsed in a killable child process, then stored in a private Supabase Storage path scoped to the user. Extracted pages, maps, progress, preferences, paths, lessons, notes, and highlights live in Postgres. Retrieval uses short-lived signed URLs. Delete removes the stored object and cascades the book's database rows. No application log contains document text, title, author, or filename.

learnbook.core.learning_path owns deterministic parent-first scheduling and has no provider or storage imports. The Next.js learning flow renders model and document text as text nodes and requires explicit consent before sending source text to Groq. The current progress count reflects user-set topic status; it is not a mastery result until recall grading is added.
