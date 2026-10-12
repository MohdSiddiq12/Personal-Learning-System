# Technical Decisions

| Technology | Status | Reason | Downside | Alternatives |
| --- | --- | --- | --- | --- |
| uv | Implemented | Provides fast dependency resolution, virtual environments, and a lockfile for reproducible setup. | Adds a required project tool beyond Python and Git. | pip with requirements files; Poetry. |
| pytest | Implemented | Keeps tests concise and has a broad plugin ecosystem. | Requires a separate test dependency and conventions. | unittest. |
| Ruff | Implemented | Combines fast Python linting and formatting with one configuration. | Its defaults and rule selection need deliberate configuration. | Black with Flake8; Pylint. |
| Pydantic | Implemented | Validates typed settings and supports environment-backed configuration. | Adds runtime dependencies and validation behavior to learn. | dataclasses with manual parsing; environ-config. |
| SQLite-first | Planned | A file-backed database keeps an initial personal deployment simple and portable. | Single-writer constraints and limited multi-user scaling. | PostgreSQL; a document store. |
| PyMuPDF | Implemented | Offers practical PDF text and page extraction capabilities while preserving page structure. | AGPL licensing has distribution and network-use implications that must be reviewed before adoption. | pypdf; pdfminer.six. |
| Streamlit | Planned | Can provide a small Python-first interface for a personal tool. | Less control over complex interaction and presentation than a dedicated web stack. | FastAPI with a separate frontend; Gradio. |

Review PyMuPDF's AGPL terms against the intended distribution model before distributing the application.