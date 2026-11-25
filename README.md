# DemandTwin

DemandTwin is a local research workspace for packaged snack concepts. It manages choice studies, fits preference models from eligible responses, and compares conditional market scenarios. RACE-Twin is the proposed research framework. A seeded sandbox supports the complete workflow without recruiting participants.

## Start on Windows

Use Python 3.13 with pip, Node.js 22 or 24 LTS, and npm. The project was also tested with Node.js 26.

On this prepared workspace, double-click **start.cmd** or run `scripts/start_all.ps1`. The launcher checks dependencies, upgrades the database, builds the production frontend when sources change, and starts both services. Keep its terminal open while using the app. Use `-Development` for frontend hot reload.

```powershell
.\scripts\setup.ps1 -Research
.\scripts\start_all.ps1
```

Open [DemandTwin](http://127.0.0.1:3000) and [FastAPI docs](http://127.0.0.1:8000/docs). Register an account, then click **Prepare demo workspace** on Overview to create a labeled synthetic study, model and price scenarios. The button reuses that account's existing demo.

The setup flag installs PyMC, ArviZ, SHAP, Matplotlib and MLflow. The base setup supports the web application and core model fitting. Setup generates a private root `.env` when one is absent, including a researcher enrollment code. Read `RESEARCH_REGISTRATION_CODE` from that file when registering a researcher. The native database defaults to `data/runtime/app.db`. To use PostgreSQL, create a database and configure `DATABASE_URL` in `.env` before startup. Native startup binds to loopback.

## Start on Linux or Docker

```bash
bash scripts/setup.sh --research
bash scripts/start_all.sh
```

For Docker, set a URL-safe `POSTGRES_PASSWORD` and a private `JWT_SECRET` of at least 32 characters in the root `.env`, then run `docker compose up --build`. Compose starts PostgreSQL, Redis, FastAPI, a Celery worker and Next.js. Use `docker compose --profile research up --build` to add MLflow, then set `MLFLOW_TRACKING_URI=http://127.0.0.1:5000` in the training shell to log offline runs there. Use `docker compose config` to inspect resolved settings locally.

The native and Docker launchers default to ports 3000 and 8000. To run both, set `DEMANDTWIN_WEB_PORT` and `DEMANDTWIN_API_PORT` in the Docker shell to unused ports before `docker compose up`. The first Docker build downloads the Python and Node environments and can take several minutes.

## Demonstration

1. Register a founder account and create a project named **Mumbai snacks**.
2. Add **Millet crisps**, INR 30, 50 g, classic flavour, with **Masala crackers**, INR 35, 50 g, as its competitor.
3. Open Consumer Lab. Create a synthetic study with the default price levels and pack contrast. Launch it and open the participant lab to try consent, six randomized tasks and withdrawal.
4. Return to the study and generate the labeled synthetic panel. Train the choice model and wait for **ready**. Rank design candidates under different policies.
5. Open Market Twin to inspect preferences and holdout scores. In Simulator compare prices **20, 30, 40**, with **1,000** illustrative opportunities. Read the evidence label and interval.
6. Generate and download a PDF from Reports. Set `RESEARCH_REGISTRATION_CODE` locally and use the code during registration to access the separate research view.

Product Studio accepts packaging uploads up to 5 MB in PNG, JPEG or WebP format. Images are validated, resized and stripped of original metadata, then stored in the database with project access controls. Owners can add registered collaborators as editors in Projects and revoke their access.

Consumer Lab supports randomized, balanced and adaptive assignment. The study stores a task budget, product and price limits, and optional segment enrollment limits. Adaptive sessions update preferences from each response and select one new eligible task at a time. Candidate exposure penalties encourage broader coverage. Notifications record study creation, training completion and report availability. Failed jobs and runs interrupted for more than 20 minutes can be retried from the study.

The app reports choices conditional on the alternatives, model and stated opportunity. A synthetic panel cannot validate Indian demand, geographic transfer, willingness to pay or launch viability.

## Reproduce the results

```powershell
.\scripts\download_data.ps1
$env:DEMANDTWIN_SHAP = '1'
.\scripts\train_models.ps1
.\.venv\Scripts\python.exe scripts/evaluate_twin.py
.\.venv\Scripts\python.exe scripts/run_research.py
.\.venv\Scripts\python.exe scripts/run_research.py --bayes --people 18 --draws 500 --tune 500
.\.venv\Scripts\python.exe scripts/evaluate_all.py
```

Linux equivalents are `bash scripts/download_data.sh`, `bash scripts/train_models.sh` and `.venv/bin/python scripts/run_research.py`. Raw data is cached and recorded by SHA-256. The UK transaction pipeline writes Parquet. The Twin-2K-500 check fetches the question catalogue and numeric response tables and saves aggregate evaluation outputs. Results live in [research/results](research/results). Offline artifacts are under `artifacts/` and app choice artifacts are serialized as JSON in the database. MLflow defaults to `data/runtime/mlflow.db` with local artifact storage. Use `mlflow server --backend-store-uri sqlite:///data/runtime/mlflow.db` from the repo root in the research environment to inspect runs.

## Verification

Run `scripts/verify.ps1` for the Python, TypeScript, production build and browser checks in one command. It uses an installed Chrome when available. Use `-SkipBrowser` to run the other checks only.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend exec -- playwright install chromium
npm.cmd --prefix frontend test
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to test with an existing Chromium browser. The browser suite starts test servers on 3009 and 8009 and uses its own local database. Set `DEMANDTWIN_TEST_POSTGRES` to a disposable PostgreSQL database to run the API suite there.

Run `python scripts/smoke_test.py --url http://127.0.0.1:8000` with the virtual environment's Python to exercise a running backend and its configured worker. It creates and removes a synthetic test project and prints a readiness result.

Run `scripts/backup.ps1` for an online database backup, or `python scripts/backup.py` on Linux. SQLite backups are integrity-checked. PostgreSQL backups use `pg_dump` custom format. Store backups privately. To check a SQLite restore, copy the backup to a separate path, point `DATABASE_URL` to that copy and start on unused ports. PostgreSQL custom dumps can be restored with `pg_restore` into a separate empty database. Stop the app and take a backup before replacing its active database.

Read the [architecture](docs/architecture/TECHNICAL_SPEC.md), [model card](docs/model_cards/CHOICE_MODEL.md), [dataset guide](docs/dataset/DATASETS.md), [ethics protocol requirements](research/ethics/PROTOCOL.md) and [verification status](PROJECT_STATUS.md). Source code is MIT licensed. Dataset rights remain source-specific.
