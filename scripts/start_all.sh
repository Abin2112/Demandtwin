#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
api_port=${1:-8000}
web_port=${2:-3000}
export API_ORIGIN="http://127.0.0.1:$api_port"
mkdir -p data/runtime
.venv/bin/python scripts/configure_local.py
PYTHONPATH=backend:ml-engine .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/doctor.py
npm --prefix frontend run build
bash scripts/start_backend.sh "$api_port" >data/runtime/api.log 2>&1 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT
ready=0
for _ in {1..40}; do
    if ! kill -0 "$api_pid" 2>/dev/null; then break; fi
    if curl -fsS --max-time 2 "$API_ORIGIN/api/v1/health" >/dev/null 2>&1; then ready=1; break; fi
    sleep 0.5
done
if [[ $ready == 0 ]]; then printf 'API startup failed. See data/runtime/api.log.\n' >&2; exit 1; fi
printf 'DemandTwin  http://127.0.0.1:%s\nAPI docs    %s/docs\n' "$web_port" "$API_ORIGIN"
bash scripts/start_frontend.sh "$web_port"
