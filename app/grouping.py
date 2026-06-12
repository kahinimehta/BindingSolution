"""Cross-project paper grouping without duplication + drop suggestions."""
from __future__ import annotations

import re
from collections import defaultdict

from .mock import _tokens

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "via",
    "under", "over", "from", "into", "using", "as", "at", "by", "is", "are", "we",
}


def norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower()).strip()


def _paper_index(projects: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for proj in projects:
        for item in proj.get("items") or []:
            out[item["key"]] = {
                "paper_key": item["key"],
                "title": item.get("title", "Untitled"),
                "project_key": proj["key"],
                "project_name": proj.get("short_name") or proj.get("name") or proj["key"],
                "tags": list(item.get("tags") or []),
                "year": item.get("year") or "",
                "norm_title": norm_title(item.get("title", "")),
            }
    return out


def complete_paper_groups(result: dict, projects: list[dict]) -> dict:
    """Ensure paper keys are valid, unique across groups, and drops reference real papers."""
    index = _paper_index(projects)
    used: set[str] = set()
    groups: list[dict] = []

    for raw in result.get("groups") or []:
        keys: list[str] = []
        projects_in: set[str] = set()
        for key in raw.get("paper_keys") or []:
            if key not in index or key in used:
                continue
            used.add(key)
            keys.append(key)
            projects_in.add(index[key]["project_key"])
        if not keys:
            continue
        papers = [
            {
                "paper_key": key,
                "title": index[key]["title"],
                "project_key": index[key]["project_key"],
            }
            for key in keys
        ]
        groups.append({
            "name": raw.get("name") or "Reading set",
            "paper_keys": keys,
            "papers": papers,
            "project_keys": sorted(projects_in),
            "rationale": (raw.get("rationale") or "").strip()
            or "Papers that belong together without overlapping other groups.",
        })

    drops: list[dict] = []
    drop_keys: set[str] = set()
    for raw in result.get("drops") or []:
        key = raw.get("paper_key")
        if not key or key not in index or key in used or key in drop_keys:
            continue
        drop_keys.add(key)
        row = index[key]
        drops.append({
            "paper_key": key,
            "title": raw.get("title") or row["title"],
            "project_key": raw.get("project_key") or row["project_key"],
            "drop_kind": raw.get("drop_kind") or "redundant",
            "reason": (raw.get("reason") or "").strip()
            or "Consider removing from your active shelf.",
        })

    overview = (result.get("overview") or "").strip()
    if not overview:
        overview = (
            f"Organized {len(used)} papers into {len(groups)} non-overlapping reading set"
            f"{'s' if len(groups) != 1 else ''}"
            + (f" and flagged {len(drops)} to drop." if drops else ".")
        )

    return {
        "overview": overview,
        "groups": groups,
        "drops": drops,
        "stats": {
            "papers_grouped": len(used),
            "num_groups": len(groups),
            "num_drops": len(drops),
            "num_projects": len(projects),
        },
    }


def heuristic_paper_groups(projects: list[dict]) -> dict:
    """Offline grouping: dedupe by title, cluster by shared tags, suggest weak fits to drop."""
    index = _paper_index(projects)
    if not index:
        return {
            "overview": "No papers to organize.",
            "groups": [],
            "drops": [],
            "stats": {"papers_grouped": 0, "num_groups": 0, "num_drops": 0, "num_projects": len(projects)},
            "_mock": True,
        }

    by_title: dict[str, list[dict]] = defaultdict(list)
    for row in index.values():
        if row["norm_title"]:
            by_title[row["norm_title"]].append(row)

    drops: list[dict] = []
    drop_keys: set[str] = set()
    for copies in by_title.values():
        if len(copies) < 2:
            continue
        copies.sort(key=lambda r: (r["project_key"], r["paper_key"]))
        keep = copies[0]
        for dup in copies[1:]:
            drop_keys.add(dup["paper_key"])
            drops.append({
                "paper_key": dup["paper_key"],
                "title": dup["title"],
                "project_key": dup["project_key"],
                "drop_kind": "duplicate",
                "reason": (
                    f"Same paper as \"{keep['title']}\" in {keep['project_name']} — "
                    "keep one copy on your shelf."
                ),
            })

    remaining = [r for r in index.values() if r["paper_key"] not in drop_keys]
    tag_index: dict[str, list[dict]] = defaultdict(list)
    for row in remaining:
        tags = set(row["tags"]) | set(_tokens(row["title"]))
        for tag in tags:
            if tag not in _STOP and len(tag) >= 3:
                tag_index[tag].append(row)

    ranked_tags = sorted(tag_index, key=lambda t: (-len(tag_index[t]), t))
    assigned: set[str] = set()
    groups: list[dict] = []

    for tag in ranked_tags:
        candidates = [r for r in tag_index[tag] if r["paper_key"] not in assigned]
        if len(candidates) < 2:
            continue
        project_keys = sorted({r["project_key"] for r in candidates})
        if len(project_keys) < 2 and len(candidates) < 3:
            continue
        keys = [r["paper_key"] for r in candidates[:10]]
        for key in keys:
            assigned.add(key)
        groups.append({
            "name": f"{tag.replace('-', ' ').title()} set",
            "paper_keys": keys,
            "project_keys": project_keys,
            "rationale": (
                f"Papers linked by \"{tag}\" across {len(project_keys)} project"
                f"{'s' if len(project_keys) != 1 else ''} — each paper appears once."
            ),
        })
        if len(groups) >= 6:
            break

    for row in remaining:
        if row["paper_key"] in assigned:
            continue
        tags = set(row["tags"]) | set(_tokens(row["title"]))
        overlap = sum(1 for t in tags if len(tag_index.get(t, [])) >= 2)
        if overlap == 0 and len(tags) <= 2:
            drop_keys.add(row["paper_key"])
            drops.append({
                "paper_key": row["paper_key"],
                "title": row["title"],
                "project_key": row["project_key"],
                "drop_kind": "weak_fit",
                "reason": (
                    f"Limited overlap with the rest of your shelf — "
                    f"consider archiving or moving out of {row['project_name']}."
                ),
            })
            continue
        assigned.add(row["paper_key"])
        groups.append({
            "name": f"{row['project_name']} — standalone",
            "paper_keys": [row["paper_key"]],
            "project_keys": [row["project_key"]],
            "rationale": "Single paper with no strong cross-project cluster.",
        })

    result = complete_paper_groups({"overview": "", "groups": groups, "drops": drops}, projects)
    result["_mock"] = True
    names = ", ".join(p.get("short_name") or p["name"] for p in projects[:4])
    extra = f" and {len(projects) - 4} more" if len(projects) > 4 else ""
    result["overview"] = (
        f"Across {len(projects)} projects ({names}{extra}), grouped {result['stats']['papers_grouped']} "
        f"papers into {result['stats']['num_groups']} non-overlapping set"
        f"{'s' if result['stats']['num_groups'] != 1 else ''}"
        + (
            f" and flagged {result['stats']['num_drops']} duplicate or weak-fit paper"
            f"{'s' if result['stats']['num_drops'] != 1 else ''} to drop."
            if result["stats"]["num_drops"]
            else "."
        )
    )
    return result
