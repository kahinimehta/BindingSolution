"""`python -m app` — start the web server (and open it in your browser)."""
from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn

from .config import get_settings


def _bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _open_browser(url: str) -> None:
    # Best-effort: never let a missing/blocked browser take down the server
    # (e.g. headless boxes, SSH sessions, containers).
    try:
        webbrowser.open_new_tab(url)
    except Exception:
        pass


def main() -> None:
    settings = get_settings()
    reload = _bool("BINDING_RELOAD")

    # Browsers can't reach 0.0.0.0/:: — point them at localhost instead.
    browser_host = "localhost" if settings.host in {"0.0.0.0", "::", ""} else settings.host
    url = f"http://{browser_host}:{settings.port}"

    banner = f"""
  BindingSolution — your AI reading room
  ──────────────────────────────────────
  ▸ {url}
  ▸ Claude model : {settings.model}{'  (MOCK — no API key)' if (settings.mock_llm or not settings.anthropic_api_key) else ''}
  ▸ Zotero       : {settings.zotero_mode or 'not configured (use the demo library)'}
"""
    print(banner)

    # Open the default browser shortly after boot, once the server is listening.
    # Skipped in --reload (dev) mode and when BINDING_NO_BROWSER is set.
    if not reload and not _bool("BINDING_NO_BROWSER"):
        threading.Timer(1.2, _open_browser, args=[url]).start()

    uvicorn.run(
        "app.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
