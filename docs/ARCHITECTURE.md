# Architecture

The deployment has two UI paths. Streamlit remains a local prototype; the public app is:

```text
Browser -> Next.js -> FastAPI -> core
						 |-> Supabase Auth / Postgres / private Storage
						 |-> Gemini (explicitly consented, BYOK only)
```

The Next.js client uses Supabase Auth for sessions and sends the access token to FastAPI. FastAPI verifies it with Supabase Auth, derives the owner ID from the verified response, and performs explicit owner-filtered repository operations. Its service-role key is server-only. Core owns extraction and document rules; core must not import either UI or API code. The local Streamlit app may import core and configuration, but core must never import Streamlit. Gemini is called only for an opted-in BYOK guide request.

PDF ingestion lives in `learnbook.core.ingestion`. Its flow is:

```text
Path or bytes -> size/header checks -> PyMuPDF validation -> ordered page text + metadata/hash
```

The ingestion module is core logic: it has no UI, database, provider, network, OCR, or rendering dependency. Its results keep each page and its 1-based page number separate so later layers can cite source locations.

The local prototype lives in `learnbook.app`; pure display transformations live in `view_models.py`. Hosted routes live in `learnbook.api`. Uploaded PDF bytes are parsed in a killable child process, then stored in a private Supabase Storage path scoped to the user; extracted pages and guides live in Postgres. Retrieval uses short-lived signed URLs. Delete removes the stored object and database rows. No application log contains document text, title, author, or filename.