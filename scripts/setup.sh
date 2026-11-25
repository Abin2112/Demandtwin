#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
requirements=backend/requirements.txt
if [[ ${1:-} == --research ]]; then requirements=backend/requirements-research.txt; fi
.venv/bin/python -m pip install -r "$requirements"
npm --prefix frontend ci --no-audit --no-fund
.venv/bin/python scripts/configure_local.py
PYTHONPATH=backend:ml-engine .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/doctor.py
