# BindingSolution — common tasks
.PHONY: help setup run dev test clean env vercel-demo
.DEFAULT_GOAL := help

help:             ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {printf "  \033[1m%-8s\033[0m %s\n", $$1, $$2}'

setup:            ## Create venv, install deps, scaffold gitignored .env
	bash scripts/setup.sh

run:              ## Start the server (http://127.0.0.1:8765)
	bash scripts/run.sh

dev:              ## Start with auto-reload (for hacking on the code)
	BINDING_RELOAD=1 bash scripts/run.sh

test:             ## Run the test suite (offline, uses MOCK_LLM)
	.venv/bin/python -m pytest -q

env:              ## (Re)create .env from the template if it is missing
	@test -f .env && echo ".env already exists — not overwriting." || \
		(cp .env.example .env && chmod 600 .env && echo "Created .env — add your keys: $${EDITOR:-nano} .env")

vercel-demo:      ## Build static demo site for Vercel (vercel/)
	.venv/bin/python scripts/build_vercel_demo.py

clean:            ## Remove venv, caches and local data (keeps .env)
	rm -rf .venv __pycache__ app/__pycache__ tests/__pycache__ .pytest_cache data
