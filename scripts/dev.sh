#!/usr/bin/env bash
# Web server and API-import thread in one process, like the container.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/gunicorn --no-control-socket --bind 127.0.0.1:5000 --workers 1 --threads 4 --timeout 120 app:app
