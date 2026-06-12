"""Unit tests for Zotero item mapping and collection roll-up logic."""
from __future__ import annotations

from app.projects import UNFILED_KEY
from app.zotero_client import (
    _fetch_collection_items,
    _fetch_unfiled_items,
    _keep_item,
    map_item,
)


def _raw(key: str, item_type: str, **fields):
    data = {"key": key, "itemType": item_type, **fields}
    return {"key": key, "data": data, "meta": {}}


class FakeZotero:
    """Minimal pyzotero stand-in for collection/item fetch tests."""

    def __init__(self, tree: dict[str, list[str]], items_by_col: dict[str, list[dict]], top: list[dict] | None = None):
        self._tree = tree
        self._items_by_col = items_by_col
        self._top = top or []

    def all_collections(self, collection_key: str):
        return [{"key": k} for k in self._tree.get(collection_key, [collection_key])]

    def collection_items_top(self, collection_key: str):
        return self._items_by_col.get(collection_key, [])

    def everything(self, first_page):
        return first_page

    def top(self):
        return self._top


def test_map_item_uses_top_level_key_fallback():
    raw = {"key": "ABCD1234", "data": {"itemType": "journalArticle", "title": "A paper"}, "meta": {}}
    assert map_item(raw)["key"] == "ABCD1234"


def test_keep_item_skips_child_attachments():
    raw = _raw("ATT1", "attachment", parentItem="PARENT1", title="paper.pdf")
    assert _keep_item(raw) is False


def test_keep_item_includes_standalone_attachments():
    raw = _raw("ATT1", "attachment", filename="notes.pdf")
    assert _keep_item(raw) is True
    assert map_item(raw)["title"] == "notes.pdf"


def test_fetch_collection_items_rolls_up_subcollections():
    zot = FakeZotero(
        tree={"PARENT": ["PARENT", "CHILD"]},
        items_by_col={
            "PARENT": [],
            "CHILD": [_raw("P1", "journalArticle", title="Nested paper", creators=[{"lastName": "Smith"}])],
        },
    )
    items = _fetch_collection_items(zot, "PARENT")
    assert len(items) == 1
    assert items[0]["title"] == "Nested paper"


def test_fetch_collection_items_dedupes_across_tree():
    zot = FakeZotero(
        tree={"PARENT": ["PARENT", "CHILD"]},
        items_by_col={
            "PARENT": [_raw("P1", "journalArticle", title="Same paper")],
            "CHILD": [_raw("P1", "journalArticle", title="Same paper")],
        },
    )
    items = _fetch_collection_items(zot, "PARENT")
    assert len(items) == 1


def test_fetch_unfiled_items():
    zot = FakeZotero(
        tree={},
        items_by_col={},
        top=[
            _raw("U1", "journalArticle", title="Loose paper"),
            _raw("U2", "journalArticle", title="In collection", collections=["COL1"]),
        ],
    )
    items = _fetch_unfiled_items(zot)
    assert len(items) == 1
    assert items[0]["key"] == "U1"


def test_unfiled_key_constant():
    assert UNFILED_KEY == "__unfiled__"
