#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export NEXT_TELEMETRY_DISABLED=1
if [[ ! -f frontend/.next/BUILD_ID ]]; then npm --prefix frontend run build; fi
exec node frontend/node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port "${1:-3000}"
