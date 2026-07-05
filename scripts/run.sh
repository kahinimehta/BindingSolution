#!/usr/bin/env bash
# Start the BindingSolution server (reads host/port/keys from .env).
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_PY=".venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "Virtualenv is missing or broken."
  echo "Recreate it with:"
  echo "  rm -rf .venv && make setup"
  exit 1
fi

if ! "$VENV_PY" -c "import uvicorn" 2>/dev/null; then
  echo "Python dependencies are not installed in .venv."
  echo "Run:"
  echo "  make setup"
  echo "If setup says the venv already exists but this keeps failing:"
  echo "  rm -rf .venv && make setup"
  exit 1
fi

PORT=$(grep -E '^PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '[:space:]' || true)
PORT=${PORT:-8765}

if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $PORT is already in use."
    echo "Stop the other server (Ctrl+C in that terminal) or set a different PORT in .env"
    exit 1
  fi
fi

exec "$VENV_PY" -m app
