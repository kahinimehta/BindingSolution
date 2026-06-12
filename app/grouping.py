"""Cross-project paper grouping without duplication + drop suggestions."""
from __future__ import annotations

import re
from collections import defaultdict

from .mock import _tokens
from .projects import (
    collection_entry_count,
    inactive_reason,
    unique_paper_count,
)

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "via",
    "under", "over", "from", "into", "using", "as", "at", "by", "is", "are", "we",
}

# Each optimal paper set should be a substantial reading batch, not a tiny cluster.
GROUP_MIN_PAPERS = 10
GROUP_MAX_PAPERS = 30


def norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower()).strip()


_GENERIC_SUMMARY = (
    "These papers share a coherent theme on your shelf. "
    "Reading them together should surface shared methods or questions without overlapping other sets."
)


def _summary_is_usable(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 40:
        return False
    return cleaned != _GENERIC_SUMMARY


def synthesize_group_summary(name: str, keys: list[str], index: dict[str, dict]) -> str:
    """Build a 2-sentence blurb from titles, tags, and collections when the model omits one."""
    rows = [index[k] for k in keys if k in index]
    if not rows:
        label = (name or "This set").strip()
        return (
            f"{label} groups related papers from your shelf. "
            "Read them together to compare how the theme shows up across collections."
        )

    project_names = sorted({r.get("project_name") or r["project_key"] for r in rows})
    proj_note = (
        f"{len(project_names)} collections ({', '.join(project_names[:3])}"
        f"{'…' if len(project_names) > 3 else ''})"
        if len(project_names) != 1
        else project_names[0]
    )

    tag_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for tag in row.get("tags") or []:
            t = tag.strip().lower()
            if t and t not in _STOP and len(t) >= 3:
                tag_counts[t] += 1
        for token in _tokens(row.get("title", "")):
            if token not in _STOP:
                tag_counts[token] += 1
    themes = [t for t, _ in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
    theme_note = ", ".join(themes) if themes else (name or "a shared theme").lower()

    sample_titles = "; ".join(f"\"{r['title']}\"" for r in rows[:3])
    if len(rows) > 3:
        sample_titles += f"; and {len(rows) - 3} more"

    return (
        f"This set gathers {len(rows)} papers on {theme_note} from {proj_note}. "
        f"Representative work includes {sample_titles}. "
        f"Read them as one arc to compare methods and findings across your shelf."
    )


def _group_summary(raw: dict, *, keys: list[str] | None = None, index: dict[str, dict] | None = None) -> str:
    text = (raw.get("summary") or raw.get("rationale") or "").strip()
    if _summary_is_usable(text):
        return text
    if keys and index is not None:
        return synthesize_group_summary(raw.get("name") or "Reading set", keys, index)
    return _GENERIC_SUMMARY


def enrich_group_summaries(result: dict, projects: list[dict]) -> dict:
    """Ensure every group has a 2+ sentence summary (repairs old or truncated Claude runs)."""
    index = _paper_index(projects)
    groups: list[dict] = []
    for grp in result.get("groups") or []:
        row = dict(grp)
        keys = list(row.get("paper_keys") or [])
        summary = _group_summary(row, keys=keys, index=index)
        row["summary"] = summary
        row["rationale"] = summary
        groups.append(row)
    out = dict(result)
    out["groups"] = groups
    return out


def _paper_tags(row: dict) -> set[str]:
    tags = {t.strip().lower() for t in (row.get("tags") or []) if t and t.strip()}
    tags |= {t for t in _tokens(row.get("title", "")) if t not in _STOP}
    return tags


def _overlap_score(paper_key: str, group_keys: list[str], index: dict[str, dict]) -> int:
    tags = _paper_tags(index[paper_key])
    if not tags:
        return 0
    score = 0
    for key in group_keys:
        score += len(tags & _paper_tags(index[key]))
    return score


def _split_group_chunks(group: dict) -> list[dict]:
    keys = list(group.get("paper_keys") or [])
    if len(keys) <= GROUP_MAX_PAPERS:
        return [group]
    name = group.get("name") or "Reading set"
    chunks: list[dict] = []
    for i, start in enumerate(range(0, len(keys), GROUP_MAX_PAPERS)):
        chunk_keys = keys[start : start + GROUP_MAX_PAPERS]
        part = dict(group)
        part["paper_keys"] = chunk_keys
        part["name"] = f"{name} ({i + 1})" if len(keys) > GROUP_MAX_PAPERS else name
        chunks.append(part)
    return chunks


def normalize_group_sizes(groups: list[dict], index: dict[str, dict]) -> list[dict]:
    """Enforce 10–30 papers per set; merge/split and absorb stragglers to cut standalone count."""
    expanded: list[dict] = []
    for group in groups:
        expanded.extend(_split_group_chunks(group))

    undersized: list[dict] = []
    sized: list[dict] = []
    for group in expanded:
        if len(group.get("paper_keys") or []) >= GROUP_MIN_PAPERS:
            sized.append(group)
        else:
            undersized.append(group)

    # Merge compatible undersized sets when the union is 10–30 papers.
    undersized.sort(key=lambda g: len(g.get("paper_keys") or []))
    merged_undersized: list[dict] = []
    used = [False] * len(undersized)
    for i, ga in enumerate(undersized):
        if used[i]:
            continue
        keys = list(ga.get("paper_keys") or [])
        name = ga.get("name") or "Reading set"
        for j in range(i + 1, len(undersized)):
            if used[j]:
                continue
            gb = undersized[j]
            combined = keys + [k for k in gb.get("paper_keys") or [] if k not in keys]
            if GROUP_MIN_PAPERS <= len(combined) <= GROUP_MAX_PAPERS:
                keys = combined
                name = f"{name} + {gb.get('name', 'Reading set')}"
                used[j] = True
                break
        used[i] = True
        if len(keys) >= GROUP_MIN_PAPERS:
            row = dict(ga)
            row["paper_keys"] = keys
            row["name"] = name
            sized.append(row)
        else:
            row = dict(ga)
            row["paper_keys"] = keys
            merged_undersized.append(row)

    pool: list[str] = []
    for group in merged_undersized:
        pool.extend(group.get("paper_keys") or [])

    # Absorb pooled papers into existing sets with thematic overlap and spare capacity.
    for group in sized:
        keys = list(group.get("paper_keys") or [])
        changed = True
        while changed and len(keys) < GROUP_MAX_PAPERS and pool:
            changed = False
            best_key = None
            best_score = 0
            for key in pool:
                score = _overlap_score(key, keys, index)
                if score > best_score:
                    best_score = score
                    best_key = key
            if best_key and best_score > 0:
                keys.append(best_key)
                pool.remove(best_key)
                changed = True
        group["paper_keys"] = keys

    # Form new sets from whatever remains in the pool (same collection / tag affinity first).
    while len(pool) >= GROUP_MIN_PAPERS:
        seed = pool.pop(0)
        keys = [seed]
        seed_tags = _paper_tags(index[seed])
        candidates = sorted(
            pool,
            key=lambda k: -_overlap_score(k, keys, index),
        )
        for key in candidates:
            if len(keys) >= GROUP_MAX_PAPERS:
                break
            if _overlap_score(key, keys, index) > 0 or index[key]["project_key"] == index[seed]["project_key"]:
                keys.append(key)
                pool.remove(key)
        if len(keys) < GROUP_MIN_PAPERS:
            pool.extend(keys)
            break
        sized.append({
            "name": f"{index[seed].get('project_name', 'Shelf')} cluster",
            "paper_keys": keys,
            "project_keys": sorted({index[k]["project_key"] for k in keys}),
            "summary": "",
            "rationale": "",
        })

    return [g for g in sized if len(g.get("paper_keys") or []) >= GROUP_MIN_PAPERS]


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
    raw_groups: list[dict] = []

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
        raw_groups.append({
            "name": raw.get("name") or "Reading set",
            "paper_keys": keys,
            "project_keys": sorted(projects_in),
            "summary": raw.get("summary") or raw.get("rationale") or "",
            "rationale": raw.get("rationale") or "",
        })

    normalized = normalize_group_sizes(raw_groups, index)
    used = {key for g in normalized for key in g.get("paper_keys") or []}
    groups: list[dict] = []
    for raw in normalized:
        keys = list(raw.get("paper_keys") or [])
        projects_in = sorted({index[k]["project_key"] for k in keys})
        papers = [
            {
                "paper_key": key,
                "title": index[key]["title"],
                "project_key": index[key]["project_key"],
            }
            for key in keys
        ]
        summary = _group_summary(raw, keys=keys, index=index)
        groups.append({
            "name": raw.get("name") or "Reading set",
            "paper_keys": keys,
            "papers": papers,
            "num_papers": len(keys),
            "project_keys": projects_in,
            "summary": summary,
            "rationale": summary,
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

    ungrouped_keys = sorted(k for k in index if k not in used and k not in drop_keys)
    ungrouped = [
        {
            "paper_key": key,
            "title": index[key]["title"],
            "project_key": index[key]["project_key"],
        }
        for key in ungrouped_keys
    ]

    total = len(index)
    overview = (result.get("overview") or "").strip()
    if not overview:
        parts = [
            f"Grouped {len(used)} of {total} papers into {len(groups)} reading set"
            f"{'s' if len(groups) != 1 else ''}",
        ]
        if ungrouped:
            parts.append(f"{len(ungrouped)} standalone")
        if drops:
            parts.append(f"{len(drops)} flagged to drop")
        overview = ", ".join(parts) + "."

    return {
        "overview": overview,
        "groups": groups,
        "drops": drops,
        "ungrouped": ungrouped,
        "stats": {
            "total_papers": total,
            "papers_grouped": len(used),
            "num_ungrouped": len(ungrouped),
            "num_groups": len(groups),
            "num_drops": len(drops),
            "num_projects": len(projects),
        },
    }


def _library_paper_index(projects: dict[str, dict] | list[dict]) -> dict[str, dict]:
    if isinstance(projects, dict):
        projects = list(projects.values())
    out: dict[str, dict] = {}
    for proj in projects:
        reason = inactive_reason(proj)
        for item in proj.get("items") or []:
            key = (item.get("key") or "").strip()
            if not key or key in out:
                continue
            out[key] = {
                "paper_key": key,
                "title": item.get("title", "Untitled"),
                "project_key": proj["key"],
                "inactive_reason": reason,
            }
    return out


def _shelf_summary(stats: dict) -> str:
    unique = stats.get("unique_papers", stats.get("shelf_papers", 0))
    grouped = stats.get("papers_grouped", 0)
    standalone = stats.get("num_ungrouped", 0)
    drops = stats.get("num_drops", 0)
    entries = stats.get("collection_entries", 0)
    extra = ""
    filings = stats.get("duplicate_filings", 0)
    if filings:
        extra = f" ({entries} collection entries; {filings} extra filings across folders)"
    return (
        f"{unique} unique papers — {grouped} in sets · {standalone} standalone · "
        f"{drops} to drop{extra}"
    )


def finalize_shelf_coverage(
    result: dict, all_projects: dict[str, dict] | list[dict],
) -> dict:
    """Place every library paper in a set, standalone, or drop bucket."""
    if isinstance(all_projects, dict):
        projects = list(all_projects.values())
    else:
        projects = all_projects

    assigned: set[str] = set()
    for grp in result.get("groups") or []:
        assigned.update(grp.get("paper_keys") or [])
    dropped = {d["paper_key"] for d in result.get("drops") or []}

    ungrouped = list(result.get("ungrouped") or [])
    seen = {p["paper_key"] for p in ungrouped}
    num_single = 0
    num_unfiled = 0

    for key, row in _library_paper_index(projects).items():
        if key in assigned or key in dropped or key in seen:
            continue
        reason = row.get("inactive_reason")
        if reason == "single":
            source = "single_paper_collection"
            num_single += 1
        elif reason == "unfiled":
            source = "unfiled"
            num_unfiled += 1
        else:
            source = "active"
        ungrouped.append({
            "paper_key": key,
            "title": row["title"],
            "project_key": row["project_key"],
            "source": source,
        })
        seen.add(key)

    ungrouped.sort(key=lambda p: (p.get("title") or "").lower())
    result["ungrouped"] = ungrouped

    grouped = len(assigned)
    drops_n = len(dropped)
    standalone_n = len(ungrouped)
    unique = unique_paper_count(projects)
    entries = collection_entry_count(projects)

    stats = result.setdefault("stats", {})
    stats.update({
        "papers_grouped": grouped,
        "num_ungrouped": standalone_n,
        "num_drops": drops_n,
        "num_single_collection": num_single,
        "num_unfiled": num_unfiled,
        "unique_papers": unique,
        "collection_entries": entries,
        "duplicate_filings": max(0, entries - unique),
        "shelf_papers": unique,
        "papers_accounted": grouped + standalone_n + drops_n,
    })
    result["shelf_summary"] = _shelf_summary(stats)
    return result


def append_single_paper_collections(
    result: dict, all_projects: dict[str, dict] | list[dict],
) -> dict:
    """Backward-compatible alias for finalize_shelf_coverage."""
    return finalize_shelf_coverage(result, all_projects)


def heuristic_paper_groups(projects: list[dict]) -> dict:
    """Offline grouping: dedupe by title, cluster by shared tags, suggest weak fits to drop."""
    index = _paper_index(projects)
    if not index:
        return {
            "overview": "No papers to organize.",
            "groups": [],
            "drops": [],
            "ungrouped": [],
            "stats": {
                "total_papers": 0,
                "papers_grouped": 0,
                "num_ungrouped": 0,
                "num_groups": 0,
                "num_drops": 0,
                "num_projects": len(projects),
            },
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
    assigned: set[str] = set()
    groups: list[dict] = []

    # Whole-collection sets when a project has 10–30 (or chunk larger folders).
    by_project: dict[str, list[dict]] = defaultdict(list)
    for row in remaining:
        by_project[row["project_key"]].append(row)
    for proj in projects:
        candidates = [r for r in by_project.get(proj["key"], []) if r["paper_key"] not in assigned]
        if len(candidates) < GROUP_MIN_PAPERS:
            continue
        for start in range(0, len(candidates), GROUP_MAX_PAPERS):
            chunk = candidates[start : start + GROUP_MAX_PAPERS]
            if len(chunk) < GROUP_MIN_PAPERS:
                break
            keys = [r["paper_key"] for r in chunk]
            assigned.update(keys)
            pname = proj.get("short_name") or proj.get("name") or proj["key"]
            part = f" ({start // GROUP_MAX_PAPERS + 1})" if len(candidates) > GROUP_MAX_PAPERS else ""
            summary = (
                f"This set gathers {len(keys)} papers from the {pname} collection. "
                f"They share a folder on your shelf and are sized for one focused reading pass. "
                f"Start here when you want depth in this project before crossing into other sets."
            )
            groups.append({
                "name": f"{pname}{part}",
                "paper_keys": keys,
                "project_keys": [proj["key"]],
                "summary": summary,
                "rationale": summary,
            })

    tag_index: dict[str, list[dict]] = defaultdict(list)
    for row in remaining:
        if row["paper_key"] in assigned:
            continue
        for tag in _paper_tags(row):
            if len(tag) >= 3:
                tag_index[tag].append(row)

    ranked_tags = sorted(tag_index, key=lambda t: (-len(tag_index[t]), t))
    for tag in ranked_tags:
        candidates = [r for r in tag_index[tag] if r["paper_key"] not in assigned]
        if len(candidates) < GROUP_MIN_PAPERS:
            continue
        keys = [r["paper_key"] for r in candidates[:GROUP_MAX_PAPERS]]
        assigned.update(keys)
        label = tag.replace("-", " ").title()
        project_keys = sorted({index[k]["project_key"] for k in keys})
        sample = ", ".join(f"\"{index[k]['title']}\"" for k in keys[:2])
        proj_note = (
            f"{len(project_keys)} collections"
            if len(project_keys) != 1
            else index[keys[0]]["project_name"]
        )
        summary = (
            f"This set groups {len(keys)} papers on {label} drawn from {proj_note}. "
            f"They connect through the \"{tag}\" thread — including {sample}. "
            f"Read them as one arc to compare how the theme shows up across your shelf."
        )
        groups.append({
            "name": f"{label} set",
            "paper_keys": keys,
            "project_keys": project_keys,
            "summary": summary,
            "rationale": summary,
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
