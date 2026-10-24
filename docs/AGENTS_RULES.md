# Agent rules (apply to every batch)

1. Work on ONE batch only. When its acceptance criteria are met, stop and write the report. Do not start the next batch.
2. Stay inside the batch scope. If you find something worth doing that is out of scope, list it under "Pending", do not do it.
3. Do not rewrite working components to match a preferred style. Change only what the batch requires.
4. Never claim something works unless you ran it in this session. Paste the exact command and the result. Anything not run goes under "Unverified".
5. If a live service (Supabase, Groq) is not configured, say so. Do not mock results and present them as real.
6. Keep tests, ruff and frontend lint passing at the end of the batch. Report the counts.
7. Update docs/PROGRESS.md and docs/BATCH_TRACKER.md at the end of every batch.
8. Write the report to docs/reports/BATCH-XX.md using the template in docs/REPORT_TEMPLATE.md.
9. If a decision needs the owner, stop and ask one specific question instead of guessing.
10. No em dashes in docs or user-facing text.