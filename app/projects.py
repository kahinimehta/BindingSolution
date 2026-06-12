"""Project usability rules shared by the API and Zotero sync."""
from __future__ import annotations

UNFILED_KEY = "__unfiled__"
UNFILED_NAME = "Library (unfiled)"
MIN_USABLE_PAPERS = 2


def item_count(proj: dict) -> int:
    return int(proj.get("num_items") or len(proj.get("items") or []))


def inactive_reason(proj: dict) -> str | None:
    """Why a project is excluded from analysis, or None if it is usable."""
    if proj.get("key") == UNFILED_KEY:
        return "unfiled"
    n = item_count(proj)
    if n == 0:
        return "empty"
    if n < MIN_USABLE_PAPERS:
        return "single"
    return None


def is_usable_project(proj: dict) -> bool:
    return inactive_reason(proj) is None


def summary_fields(proj: dict) -> dict:
    reason = inactive_reason(proj)
    return {"usable": reason is None, "inactive_reason": reason}


def usable_projects(projects: dict[str, dict]) -> list[dict]:
    return [p for p in projects.values() if is_usable_project(p)]


def total_papers(projects: list[dict]) -> int:
    return sum(item_count(p) for p in projects)


def _project_list(projects: dict[str, dict] | list[dict]) -> list[dict]:
    if isinstance(projects, dict):
        return list(projects.values())
    return projects


def collection_entry_count(projects: dict[str, dict] | list[dict]) -> int:
    """Sum of per-collection item counts — the same Zotero item in N folders counts N times."""
    return sum(item_count(p) for p in _project_list(projects))


def unique_paper_count(projects: dict[str, dict] | list[dict]) -> int:
    """Distinct Zotero item keys — how grouping deduplicates your shelf."""
    keys: set[str] = set()
    for proj in _project_list(projects):
        for item in proj.get("items") or []:
            key = (item.get("key") or "").strip()
            if key:
                keys.add(key)
    return len(keys)


def library_paper_count(projects: dict[str, dict] | list[dict]) -> int:
    """Alias for collection_entry_count (backward compatible)."""
    return collection_entry_count(projects)
