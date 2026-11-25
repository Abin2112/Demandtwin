# Architecture and research decisions

- Use FastAPI, SQLAlchemy and Alembic with PostgreSQL in Compose. Native development defaults to SQLite so the app can start without an external daemon. The same domain models and migrations were tested on both dialects.
- Use a Next.js App Router frontend with a same-origin API proxy. Local model execution is synchronous by default for development. Configure a Redis broker and Celery worker for queued execution.
- Scope founder and researcher data to project owners. Use signed short-lived access tokens and rotating refresh tokens. Participants use separately scoped, opaque consent/withdrawal credentials and provide no contact details.
- Keep UCI retail transaction benchmarks and sandbox choice data in separate evaluation tracks. UCI records do not contain exposed but rejected alternatives. Do not treat transaction-derived repeat labels as product choice outcomes.
- Train market scenario models on consented, provenance-labeled choice tasks. The development path uses synthetic observations. Keep real collection disabled pending an approved protocol.
- Store fitted coefficients and metadata in JSON rather than loading executable pickles in the API. Store benchmark artifacts separately.
- Use a separate question-transition benchmark for the Twin-2K-500 numeric response subset. Earlier hypothetical answers are inputs, later answers are targets, and participants are disjoint across training and evaluation.
- Use MIT for project code and documentation. Track third-party dataset rights separately, and keep raw data, local credentials, and binaries outside source control.
- Support registered collaborators as project editors. Project deletion and membership management remain owner actions.
- Store validated packaging images in the database so access control, deletion and backups follow the product lifecycle.
- Apply adaptive assignments one task at a time using optimistic integer versions. Preserve existing random study assignments and use enrollment quotas to limit segment counts.
- Claim each training attempt with a UUID. Retry failed runs and runs interrupted for more than 20 minutes, and prevent stale attempts from overwriting a replacement.
- Use a production frontend for the Windows double-click launcher, with explicit development mode and startup diagnostics.
