"""Build reading plans from project-spec relevance results."""
from __future__ import annotations

import copy

from .projects import is_usable_project


def projects_from_spec(spec: dict, all_projects: dict[str, dict]) -> list[dict]:
    """Return usable projects containing only papers flagged relevant for the spec."""
    analysis = spec.get("analysis") or {}
    if not analysis:
        return []

    papers_by_project: dict[str, set[str]] = {}
    for paper_key, hit in analysis.items():
        pkey = hit.get("project_key")
        if pkey:
            papers_by_project.setdefault(pkey, set()).add(paper_key)

    projects: list[dict] = []
    for pkey, paper_keys in papers_by_project.items():
        raw = all_projects.get(pkey)
        if raw is None or not is_usable_project(raw):
            continue
        proj = copy.deepcopy(raw)
        proj["items"] = [it for it in proj.get("items") or [] if it["key"] in paper_keys]
        if proj["items"]:
            projects.append(proj)
    projects.sort(key=lambda p: p["name"].lower())
    return projects


def attach_spec_mapping(plan: dict, spec: dict) -> dict:
    """Merge spec relevance onto plan steps and order core papers before supporting."""
    analysis = spec.get("analysis") or {}
    sequence = []
    for step in plan.get("sequence") or []:
        row = dict(step)
        hit = analysis.get(row.get("paper_key", ""))
        if hit:
            row["spec_relevance"] = hit.get("relevance")
            row["spec_score"] = hit.get("score")
            row["spec_why"] = hit.get("relevance_explanation")
            why = (hit.get("relevance_explanation") or "").strip()
            if why:
                base = (row.get("reason") or "").strip()
                row["reason"] = why if not base else f"{why} {base}"
        sequence.append(row)

    def sort_key(step: dict) -> tuple:
        hit = analysis.get(step.get("paper_key", ""), {})
        rel = hit.get("relevance", "supporting")
        tier = 0 if rel == "core" else 1
        return (tier, -(hit.get("score") or 0), step.get("title", ""))

    sequence.sort(key=sort_key)
    out = dict(plan)
    out["sequence"] = sequence
    out["spec_id"] = spec["id"]
    out["spec_title"] = spec["title"]
    return out
