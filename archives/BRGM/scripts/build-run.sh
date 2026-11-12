#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."   # repo root

# Ensure we call the real docker (bypass aliases/functions)
DOCKER_BIN="$(command -v docker)"
if [[ -z "$DOCKER_BIN" ]]; then
  echo "Docker CLI not found in PATH" >&2; exit 1
fi

# Example build+run
command "$DOCKER_BIN" build --progress=plain -t smartbiblia/brgm-publications-explorer:latest .
command "$DOCKER_BIN" run --rm -p 5000:5000 -v $(pwd)/instance:/app/instance -v $(pwd)/static/data/uploads:/app/static/data/uploads smartbiblia/brgm-publications-explorer:latest