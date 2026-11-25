#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
track=${1:-all}
if [[ $track != sandbox ]]; then .venv/bin/python scripts/preprocess_all.py; fi
exec .venv/bin/python scripts/train_all.py --track "$track"
