#!/usr/bin/env bash
# Run the app locally on port 5000, the same way as the container.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/gunicorn --no-control-socket --bind 127.0.0.1:5000 --workers 1 --threads 4 --timeout 120 app:app
