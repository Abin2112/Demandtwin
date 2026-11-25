#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend:ml-engine
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${1:-8000}"
