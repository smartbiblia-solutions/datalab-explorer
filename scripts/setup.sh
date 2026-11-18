#!/usr/bin/env bash
# Local development environment: a Python virtual environment, nothing to build.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
