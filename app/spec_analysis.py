"""Incremental spec library screening helpers."""
from __future__ import annotations

PaperRow = tuple[str, dict]


def current_paper_keys(papers: list[PaperRow]) -> set[str]:
    return {paper["key"] for _, paper in papers if paper.get("key")}


def bootstrap_screened_keys(spec: dict, papers: list[PaperRow]) -> set[str]:
    """Infer screened keys for specs saved before incremental screening."""
    stored = set(spec.get("screened_keys") or [])
    if stored:
        return stored
    if spec.get("status") != "analyzed":
        return set()
    current = current_paper_keys(papers)
    if spec.get("num_screened", 0) == len(papers) and current:
        return current
    return set(spec.get("analysis", {}).keys())


def papers_to_screen(spec: dict, papers: list[PaperRow]) -> tuple[list[PaperRow], set[str], int]:
    """Return papers needing screening, the screened-key set, and skip count."""
    current = current_paper_keys(papers)
    screened = bootstrap_screened_keys(spec, papers) & current
    to_screen = [(pk, paper) for pk, paper in papers if paper.get("key") not in screened]
    skipped = len(papers) - len(to_screen)
    return to_screen, screened, skipped


def prune_analysis(analysis: dict[str, dict], current_keys: set[str]) -> dict[str, dict]:
    return {k: v for k, v in (analysis or {}).items() if k in current_keys}
