#!/usr/bin/env bash
# Start the BindingSolution server (reads host/port/keys from .env).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "No .venv found — run 'bash scripts/setup.sh' (or 'make setup') first."
  exit 1
fi

exec .venv/bin/python -m app
