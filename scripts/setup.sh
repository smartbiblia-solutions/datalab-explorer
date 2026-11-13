#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
# Node is only needed to rebuild frontend/*.ts into static/dist (committed).
npm ci
npm run build
