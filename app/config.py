"""Environment-driven configuration.

All secrets live in the gitignored `.env` at the repo root (see
`.env.example` / docs/CONFIGURATION.md). Settings are re-read on each
`get_settings()` call so tests and long-running servers always see the
current environment.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

load_dotenv(ROOT_DIR / ".env")

DEFAULT_MODEL = "claude-opus-4-8"


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.model = os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL
        self.zotero_library_id = os.getenv("ZOTERO_LIBRARY_ID", "").strip()
        self.zotero_api_key = os.getenv("ZOTERO_API_KEY", "").strip()
        self.zotero_library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "").strip() or "user"
        self.zotero_local = _bool("ZOTERO_LOCAL")
        self.host = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
        self.port = int(os.getenv("PORT", "8765") or 8765)
        self.data_dir = Path(os.getenv("BINDING_DATA_DIR", "").strip() or (ROOT_DIR / "data"))
        self.mock_llm = _bool("MOCK_LLM")

    @property
    def anthropic_configured(self) -> bool:
        return self.mock_llm or bool(self.anthropic_api_key)

    @property
    def zotero_configured(self) -> bool:
        if self.zotero_local:
            return True
        return bool(self.zotero_library_id and self.zotero_api_key)

    @property
    def zotero_mode(self) -> str | None:
        if self.zotero_local:
            return "local"
        if self.zotero_configured:
            return "web"
        return None


def get_settings() -> Settings:
    return Settings()
