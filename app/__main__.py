"""`python -m app` — start the web server."""
from __future__ import annotations

import os

import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    reload = os.getenv("BINDING_RELOAD", "").strip().lower() in {"1", "true", "yes", "on"}

    banner = f"""
  BindingSolution — your AI reading room
  ──────────────────────────────────────
  ▸ http://{settings.host}:{settings.port}
  ▸ Claude model : {settings.model}{'  (MOCK — no API key)' if (settings.mock_llm or not settings.anthropic_api_key) else ''}
  ▸ Zotero       : {settings.zotero_mode or 'not configured (use the demo library)'}
"""
    print(banner)

    uvicorn.run(
        "app.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
