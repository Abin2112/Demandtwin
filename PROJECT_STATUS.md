# DemandTwin development status

## Readiness update · 25 November 2026

Implemented project editors with revocable access, validated database-backed packaging images, persistent notifications, a reusable synthetic demo, sequential adaptive/balanced assignment, participant task and price limits, segment quotas, interrupted training retries and online backups. Native migrations include assignment versioning and API timestamps consistently include their UTC offset.

Verified eleven Python tests on SQLite and eleven on PostgreSQL, two complete browser workflows, TypeScript checking and production frontend builds on Windows and Docker. The Docker production frontend passed the HTTP smoke workflow through PostgreSQL, Redis and a real Celery worker. Redis AOF persistence is enabled and the worker reconnected after Redis was recreated. SQLite backup integrity and PostgreSQL custom backup readability were verified.

## Verified sprint checklist

| Sprint | Verification |
| --- | --- |
| 0 · Environment | Empty workspace initialized with Git. Python 3.13, Node 26, npm and PostgreSQL 16 inspected. Docker Desktop's Linux engine was unavailable. |
| 1 · Foundation | Next.js production build, FastAPI OpenAPI, Alembic upgrades on native SQLite and PostgreSQL 16. Compose configuration parsed. |
| 2 · Data | Verified UCI archive and Twin-2K-500 numeric subset by format and SHA-256. Preprocessed UK retail to Parquet and saved measured EDA. |
| 3 · Experiments | Founder and researcher roles, project isolation, concepts and variants, consent, randomized assignment, choices and withdrawal. |
| 4 · Baselines | Trained logistic regression, random forest and XGBoost on the UK transaction target. Trained conditional logit on sandbox choices. Saved artifacts, metrics and MLflow runs. |
| 5 · Hierarchy | Verified empirical Bayes segment preferences, Laplace intervals and model-based contributions. Completed the offline four-chain PyMC sandbox fit with max R-hat 1.0088, minimum ESS 633.7 and zero divergences. |
| 6 · RACE-Twin | Verified adaptive recommendation, randomized and balanced comparators, and synthetic preference updates. Tested purchase-anchored evidence eligibility with synthetic data. |
| 7 · Simulation | Verified alternative shares, normalized segment weights, conditional units, parameter intervals, sensitivity, extrapolation flags and PDF export. |
| 8 · Backend | Verified authorization, validation, transaction consistency, native synchronous training, an in-memory Celery test worker and production Redis-backed queued execution. |
| 9 · Frontend | Verified sign-in, CRUD entry points, participant experience, comparison charts, reporting, persistent themes and mobile navigation. |
| 10 · Integration | Eleven Python tests passed on each database engine. Two browser workflows passed the founder and participant journeys. Production Docker smoke checks verified image upload, queued training, adaptive assignment, simulation, notifications, withdrawal and PDF download. |
| 11 · Research | Executed UK repeat-purchase, US repeated-question fidelity, and synthetic model, design and update benchmarks. Human snack-study experiments are pending. |
| 12 · Delivery | Windows launcher smoke-tested, PowerShell and Bash scripts parsed, seven notebook code cells compiled, and generated PDF visually checked. Architecture, model card, study protocol and manuscript draft delivered. |

## Data and model outputs

- Online Retail · 541,909 source rows and 348,872 retained UK purchase lines. The repeat-invoice benchmark uses a disjoint-customer temporal split.
- Twin-2K-500 · question catalogue plus two numeric tables for 2,058 participants. Only 40 repeated hypothetical pricing items enter the benchmark.
- Synthetic choice panel · 90 generated participants and 540 choices. Snack scenarios remain evidence-labeled. No participant recruitment took place.
- Versioned dataset rights and local acquisition status are in [the catalogue](data/metadata/dataset_catalogue.json).
- Observed scores and reproduction instructions are in the [experiment report](research/results/EXPERIMENT_REPORT.md) and [README](README.md).

## Open scope and dependencies

- Indian expenditure microdata requires a MoSPI account. Open Food Facts ingestion requires an identifying project URL or contact. Amazon grocery review redistribution rights remain unconfirmed. No data from these three sources was incorporated.
- Docker builds and the complete PostgreSQL/Redis/Celery stack were verified. Verification containers are stopped after testing. Use the native launcher for the prepared local workspace, or start Compose to use its separate PostgreSQL data volume.
- The app supports approved consent and hypothetical choice collection. Incentivized collection, observed purchase anchoring, causal price validation and Mumbai-to-city transfer require eligible, approved studies.
- Studies can assign tasks adaptively with per-session preference updates, exposure penalties, saved task budgets, price/product limits and optional segment enrollment quotas. Human sample-efficiency and coverage claims require prospective evaluation.
- Project owners can grant and revoke editor access. Product packaging uploads and private in-app notifications are implemented. Public hosting still requires a chosen domain, TLS configuration and an operational retention policy.
- The application serves the Laplace artifact. The full Bayesian fit was verified offline on synthetic choices. No human posterior was fit.

The next research milestone is a preregistered, institutionally approved snack-choice study with aligned purchase opportunities and a separate held-out task bank.
