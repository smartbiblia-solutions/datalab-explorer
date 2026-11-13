#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 required"'
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements.lock
npm ci --cache "${TMPDIR:-/tmp}/datalab-npm-cache" --no-audit --no-fund
npm run typecheck
npm run build
.venv/bin/python -m pip check
