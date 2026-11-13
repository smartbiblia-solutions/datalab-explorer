#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/gunicorn --no-control-socket --bind 127.0.0.1:5000 --workers 1 --timeout 120 app:app
