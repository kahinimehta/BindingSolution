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
