#!/usr/bin/env bash
# BindingSolution one-shot setup: venv + dependencies + .env scaffold.
set -euo pipefail

cd "$(dirname "$0")/.."

bold=$(tput bold 2>/dev/null || true)
dim=$(tput dim 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
yellow=$(tput setaf 3 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

say()  { printf '%s\n' "${1-}"; }
step() { printf '%s▸ %s%s\n' "$bold" "$1" "$reset"; }

say "${bold}BindingSolution${reset} ${dim}— setup${reset}"
say ""

# 1. Python check ------------------------------------------------------
PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  say "${yellow}python3 not found.${reset} Install Python 3.10+ and re-run."
  exit 1
fi
PYVER=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  say "${yellow}Python $PYVER found, but 3.10+ is required.${reset}"
  exit 1
fi
step "Python $PYVER"

# 2. Virtualenv --------------------------------------------------------
if [ ! -d .venv ]; then
  step "Creating virtualenv (.venv)"
  "$PYTHON" -m venv .venv
else
  step "Virtualenv already exists (.venv)"
fi

# 3. Dependencies ------------------------------------------------------
step "Installing dependencies"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

# Live Zotero sync is optional (some systems can't build a transitive dep).
# Install it best-effort so a failure never blocks setup — the demo library
# and every AI feature work without it.
if .venv/bin/pip install --quiet -r requirements-zotero.txt 2>/dev/null; then
  step "Zotero sync enabled (pyzotero installed)"
else
  say "  ${dim}(Skipped optional pyzotero — live Zotero sync unavailable; demo library still works.${reset}"
  say "  ${dim} Retry later with: .venv/bin/pip install -r requirements-zotero.txt)${reset}"
fi

# 4. .env scaffold (gitignored; holds your API keys) -------------------
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  step "Created .env from .env.example  ${dim}(gitignored, chmod 600)${reset}"
else
  step ".env already exists — leaving it untouched"
fi

say ""
say "${green}${bold}Setup complete.${reset}"
say ""
say "Next steps:"
say "  1. Add your keys:        ${bold}\${EDITOR:-nano} .env${reset}"
say "     ${dim}ANTHROPIC_API_KEY  → https://console.anthropic.com/settings/keys${reset}"
say "     ${dim}ZOTERO_LIBRARY_ID + ZOTERO_API_KEY → https://www.zotero.org/settings/keys${reset}"
say "  2. Start the server:     ${bold}make run${reset}"
say "  3. Open:                 ${bold}http://127.0.0.1:8765${reset}"
say ""
say "${dim}No keys yet? 'make run' still works — load the demo library from the UI.${reset}"
