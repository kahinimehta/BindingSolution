"""Read-only access to a Zotero library.

Supports both the Zotero Web API (library id + API key) and the local
Zotero 7 HTTP API (`ZOTERO_LOCAL=true`, no key needed — Zotero must be
running with "Allow other applications…" enabled in Settings → Advanced).

Each Zotero *collection* (folder) becomes a BindingSolution *project*.
"""
from __future__ import annotations

import re
from typing import Callable

from .config import Settings

ProgressFn = Callable[[int, int, str], None]

_SKIP_ITEM_TYPES = {"attachment", "note", "annotation"}


def _connect(settings: Settings):
    from pyzotero import zotero  # imported lazily: not needed in demo mode

    if settings.zotero_local:
        return zotero.Zotero(settings.zotero_library_id or "0", "user", local=True)
    return zotero.Zotero(
        settings.zotero_library_id,
        settings.zotero_library_type,
        settings.zotero_api_key,
    )


def _format_creators(creators: list[dict] | None) -> str:
    names = []
    for c in creators or []:
        name = c.get("lastName") or c.get("name")
        if name:
            names.append(name)
    if not names:
        return ""
    if len(names) <= 3:
        return ", ".join(names)
    return f"{names[0]} et al."


def _year(raw: dict) -> str:
    text = (raw.get("meta", {}).get("parsedDate") or raw.get("data", {}).get("date") or "")
    match = re.search(r"\b(\d{4})\b", text)
    return match.group(1) if match else ""


def map_item(raw: dict) -> dict:
    data = raw.get("data", {})
    return {
        "key": data.get("key", ""),
        "title": (data.get("title") or "(untitled)").strip(),
        "creators": _format_creators(data.get("creators")),
        "year": _year(raw),
        "item_type": data.get("itemType", ""),
        "abstract": (data.get("abstractNote") or "").strip(),
        "doi": (data.get("DOI") or "").strip(),
        "url": (data.get("url") or "").strip(),
        "publication": (
            data.get("publicationTitle")
            or data.get("bookTitle")
            or data.get("proceedingsTitle")
            or data.get("repository")
            or ""
        ).strip(),
        "tags": [t.get("tag") for t in data.get("tags", []) if t.get("tag")],
    }


def fetch_projects(settings: Settings, progress: ProgressFn | None = None) -> dict[str, dict]:
    """Fetch every collection and its top-level items. Returns {key: project}."""
    zot = _connect(settings)
    collections = zot.everything(zot.collections())
    by_key = {c["key"]: c["data"] for c in collections}

    def full_name(key: str) -> str:
        parts: list[str] = []
        cur = by_key.get(key)
        seen: set[str] = set()
        while cur is not None:
            parts.append(cur.get("name", ""))
            parent = cur.get("parentCollection")
            if not parent or parent in seen:
                break
            seen.add(parent)
            cur = by_key.get(parent)
        return " / ".join(reversed([p for p in parts if p]))

    projects: dict[str, dict] = {}
    total = len(collections)
    for index, col in enumerate(collections, start=1):
        key = col["key"]
        name = by_key[key].get("name", "")
        if progress:
            progress(index, total, name)
        raw_items = zot.everything(zot.collection_items_top(key))
        items = [map_item(it) for it in raw_items]
        items = [it for it in items if it["item_type"] not in _SKIP_ITEM_TYPES]
        items.sort(key=lambda it: (it["year"] or "0000", it["title"]))
        projects[key] = {
            "key": key,
            "name": full_name(key) or name,
            "short_name": name,
            "parent": by_key[key].get("parentCollection") or None,
            "num_items": len(items),
            "items": items,
        }
    return projects
