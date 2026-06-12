"""Read-only access to a Zotero library.

Supports both the Zotero Web API (library id + API key) and the local
Zotero 7 HTTP API (`ZOTERO_LOCAL=true`, no key needed — Zotero must be
running with "Allow other applications…" enabled in Settings → Advanced).

Each Zotero *collection* (folder) becomes a BindingSolution *project*.
Items in subcollections are rolled up into ancestor collections so parent
folders show the full paper count. Items not in any collection are grouped
under a synthetic "Library (unfiled)" project.
"""
from __future__ import annotations

import re
from typing import Callable

from .config import Settings
from .projects import UNFILED_KEY, UNFILED_NAME

ProgressFn = Callable[[int, int, str], None]

_SKIP_ITEM_TYPES = {"note", "annotation"}


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


def _item_key(raw: dict) -> str:
    data = raw.get("data", {})
    return (data.get("key") or raw.get("key") or "").strip()


def _keep_item(raw: dict) -> bool:
    """Return True for bibliographic entries and standalone files worth showing."""
    data = raw.get("data", {})
    item_type = data.get("itemType", "")
    if item_type in _SKIP_ITEM_TYPES:
        return False
    if item_type == "attachment":
        # Child PDFs/notes under a paper are fetched via the parent entry.
        if data.get("parentItem"):
            return False
        title = (data.get("title") or data.get("filename") or "").strip()
        return bool(title)
    return bool(item_type)


def map_item(raw: dict) -> dict:
    data = raw.get("data", {})
    item_type = data.get("itemType", "")
    title = (data.get("title") or "").strip()
    if item_type == "attachment" and not title:
        title = (data.get("filename") or "(untitled file)").strip()
    return {
        "key": _item_key(raw),
        "title": title or "(untitled)",
        "creators": _format_creators(data.get("creators")),
        "year": _year(raw),
        "item_type": item_type,
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


def _collection_tree_keys(zot, collection_key: str) -> list[str]:
    """Collection key plus every descendant subcollection key."""
    try:
        tree = zot.all_collections(collection_key)
    except Exception:
        return [collection_key]
    if not tree:
        return [collection_key]
    keys: list[str] = []
    seen: set[str] = set()
    for col in tree:
        key = col.get("key") if isinstance(col, dict) else None
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys or [collection_key]


def _fetch_collection_items(zot, collection_key: str) -> list[dict]:
    """Bibliographic items in a collection and all of its subcollections."""
    seen: set[str] = set()
    items: list[dict] = []
    for ck in _collection_tree_keys(zot, collection_key):
        raw_items = zot.everything(zot.collection_items_top(ck))
        for raw in raw_items:
            if not _keep_item(raw):
                continue
            mapped = map_item(raw)
            if not mapped["key"] or mapped["key"] in seen:
                continue
            seen.add(mapped["key"])
            items.append(mapped)
    items.sort(key=lambda it: (it["year"] or "0000", it["title"]))
    return items


def _fetch_unfiled_items(zot) -> list[dict]:
    """Top-level library items that belong to no collection."""
    items: list[dict] = []
    raw_items = zot.everything(zot.top())
    for raw in raw_items:
        data = raw.get("data", {})
        if data.get("collections"):
            continue
        if not _keep_item(raw):
            continue
        mapped = map_item(raw)
        if mapped["key"]:
            items.append(mapped)
    items.sort(key=lambda it: (it["year"] or "0000", it["title"]))
    return items


def fetch_projects(settings: Settings, progress: ProgressFn | None = None) -> dict[str, dict]:
    """Fetch every collection and its items. Returns {key: project}."""
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
        items = _fetch_collection_items(zot, key)
        projects[key] = {
            "key": key,
            "name": full_name(key) or name,
            "short_name": name,
            "parent": by_key[key].get("parentCollection") or None,
            "num_items": len(items),
            "items": items,
        }

    unfiled = _fetch_unfiled_items(zot)
    if unfiled:
        projects[_UNFILED_KEY] = {
            "key": _UNFILED_KEY,
            "name": _UNFILED_NAME,
            "short_name": _UNFILED_NAME,
            "parent": None,
            "num_items": len(unfiled),
            "items": unfiled,
        }

    return projects
