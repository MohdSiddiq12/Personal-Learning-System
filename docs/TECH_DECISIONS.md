# Technical Decisions

| Technology | Status | Reason | Downside | Alternatives |
| --- | --- | --- | --- | --- |
| uv | Implemented | Provides fast dependency resolution, virtual environments, and a lockfile for reproducible setup. | Adds a required project tool beyond Python and Git. | pip with requirements files; Poetry. |
| pytest | Implemented | Keeps tests concise and has a broad plugin ecosystem. | Requires a separate test dependency and conventions. | unittest. |
| Ruff | Implemented | Combines fast Python linting and formatting with one configuration. | Its defaults and rule selection need deliberate configuration. | Black with Flake8; Pylint. |
| Vitest, Testing Library, jsdom | Implemented (dev only) | Runs isolated React component tests in a DOM-like environment without adding production dependencies. | Adds development packages and a test configuration to maintain. | Jest with Testing Library and jsdom. |
| Pydantic | Implemented | Validates typed settings and supports environment-backed configuration. | Adds runtime dependencies and validation behavior to learn. | dataclasses with manual parsing; environ-config. |
| SQLite-first | Superseded | The original single-user plan was replaced by account isolation for public deployment. | Supabase adds an external service and RLS/migration obligations. | SQLite for local-only; PostgreSQL on another host. |
| PyMuPDF | Implemented | Offers practical PDF text and page extraction capabilities while preserving page structure. | AGPL licensing has distribution and network-use implications that must be reviewed before adoption. | pypdf; pdfminer.six. |
| Streamlit | Implemented | Provides a local Python-first interface for uploading, browsing, searching, and exporting extracted PDF text. | Limited highlight/notes UX; its rerun-on-interaction model needs session-state care; upload size is capped by server config. | FastAPI with a separate frontend; Gradio. |
| Next.js | Implemented | Provides the public account/library UI and responsive learning-guide interface. | Separate Node deployment and frontend/API configuration. | React/Vite; Streamlit. |
| FastAPI | Implemented | Keeps the Python ingestion core behind an authenticated API and supports process-isolated PDF work. | Requires production hosting, CORS, and API abuse controls. | Django REST; serverless Python functions. |
| Supabase Auth/Postgres/Storage | Implemented (scaffold) | Provides hosted login, owner-scoped rows, private PDF objects, and signed retrieval for online access. | Free projects can pause; RLS and service-role handling require careful review; quotas can change. | Managed Postgres + object storage + separate auth provider. |
| Gemini BYOK | Implemented (external call unverified) | Avoids a shared model bill and lets users choose their account tier after a data-use notice. | Setup friction; users pay Google; free-tier data-use terms differ from paid tier. | Owner-funded capped budget; local model. |
| Vercel + Render | Planned | Vercel supports the Next app and Render can run the FastAPI Docker image. | Two hosts, CORS, secrets, free-tier sleeps/resource limits. | Streamlit Community Cloud for prototype; Docker/Cloud Run/Fly for one container platform. |

Review PyMuPDF's AGPL terms against the intended distribution model before distributing the application.
