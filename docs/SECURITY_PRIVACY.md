# Security and privacy notes

## Model data flow

Book-map and lesson generation is optional and requires explicit consent. The API sends the source passages needed for that requested generation to Groq using a server-side `GROQ_API_KEY`. The key is never sent to the browser, stored in a database, or written to application logs. Do not log prompts, extracted book text, filenames, model output, access tokens, or API keys.

The project owner must review Groq's current data-retention, logging, and usage terms for the account and model in use before public launch. Do not promise that provider data is retained or deleted on a particular schedule until the applicable terms are verified. Update the UI notice and public terms if the provider or data flow changes.

## Generation limits and job storage

Generation uses a server-side token budget, per-request token cap, process-local token bucket and single-flight request lock, plus per-user daily job limits. The job database stores consent time, job progress, candidate results for completed chunks, and actual token counts. Job and result tables have owner-scoped RLS. The provider key is not stored with jobs.

The current limiter is process-local. Deploy one API instance only until a shared queue, distributed rate limiter, and distributed budget reservation are implemented. A restarted server interrupts active work; stored chunks remain available for retry after the heartbeat is recognized as stale.

## Other protections

- Supabase service-role and Groq credentials belong only in backend environment settings.
- All book and model text is untrusted input. Prompts identify it as data, and output is validated against Pydantic schemas.
- Document and model content is rendered as text, never injected as HTML.
- Authenticated routes derive the owner from a verified Supabase token and filter stored rows by owner.
- New migrations enable RLS and include owner policies. Verify them with two real Supabase accounts before launch.
- Public terms, copyright response contact, account recovery, abuse reporting, deletion, and legal review remain launch responsibilities.
