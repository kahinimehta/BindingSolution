"""Assemble shelf context for the chat assistant from the local store."""
from __future__ import annotations

import re
import textwrap
from typing import Any

from .projects import unique_paper_count, usable_projects

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "via",
    "under", "over", "from", "into", "using", "as", "at", "by", "is", "are", "we",
    "what", "which", "who", "how", "why", "when", "where", "my", "your", "about",
}


def _tokens(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (text or "").lower())
        if w not in _STOP
    }


def _short(text: str, width: int = 280) -> str:
    return textwrap.shorten((text or "").strip(), width=width, placeholder=" …")


def _paper_line(item: dict, *, abstract: bool = False) -> str:
    head = f"[{item['key']}] \"{item.get('title', 'Untitled')}\""
    meta = ", ".join(filter(None, [item.get("creators"), item.get("year")]))
    if meta:
        head += f" ({meta})"
    lines = [head]
    tags = item.get("tags") or []
    if tags:
        lines.append(f"  tags: {', '.join(tags[:8])}")
    if abstract and item.get("abstract"):
        lines.append(f"  abstract: {_short(item['abstract'], 220)}")
    return "\n".join(lines)


def _score_paper(item: dict, query_tokens: set[str]) -> int:
    if not query_tokens:
        return 0
    hay = " ".join([
        item.get("title", ""),
        " ".join(item.get("tags") or []),
        item.get("abstract", ""),
    ]).lower()
    return sum(1 for t in query_tokens if t in hay)


def assemble_chat_context(store: Any, message: str, scope: dict | None = None) -> str:
    """Build a token-bounded context block from everything already in library.json."""
    scope = scope or {}
    projects = store.get_projects()
    usable = usable_projects(projects)
    if scope.get("project_keys"):
        keys = set(scope["project_keys"])
        usable = [p for p in usable if p["key"] in keys]
    query_tokens = _tokens(message)

    parts: list[str] = []
    unique = unique_paper_count(projects)
    parts.append(
        f"Shelf: {len(projects)} collections ({len(usable)} active), "
        f"{unique} unique papers synced locally."
    )

    meta = store.get_meta() or {}
    if meta.get("source"):
        parts.append(f"Source: {meta['source']}.")

    for proj in usable:
        cat = proj.get("category") or {}
        line = f"\n### [{proj['key']}] {proj.get('short_name') or proj['name']} ({len(proj.get('items') or [])} papers)"
        if cat:
            line += (
                f"\nCategory: {cat.get('category', '')} ({cat.get('discipline', '')})"
                f"\nSummary: {_short(cat.get('summary', ''), 320)}"
            )
            themes = cat.get("themes") or []
            if themes:
                line += f"\nThemes: {', '.join(themes[:6])}"
        parts.append(line)

    connections = store.get_connections()
    if connections:
        parts.append("\n## Connections (saved analysis)")
        parts.append(_short(connections.get("overview", ""), 400))
        for thread in (connections.get("shared_threads") or [])[:6]:
            parts.append(
                f"- {thread.get('label')}: {thread.get('explanation', '')} "
                f"(projects: {', '.join(thread.get('project_keys') or [])})"
            )

    groups = store.get_paper_groups()
    if groups:
        parts.append("\n## Paper groups (saved analysis)")
        parts.append(_short(groups.get("overview", ""), 400))
        for grp in (groups.get("groups") or [])[:8]:
            n = grp.get("num_papers") or len(grp.get("paper_keys") or [])
            parts.append(
                f"- {grp.get('name')} ({n} papers): "
                f"{_short(grp.get('summary') or grp.get('rationale', ''), 240)}"
            )

    strategies = store.list_strategies()
    if strategies:
        parts.append("\n## Reading strategies")
        for strat in strategies[:4]:
            plan = strat.get("plan") or {}
            seq = plan.get("sequence") or []
            parts.append(
                f"- Goal: {_short(strat.get('goal', ''), 120)} "
                f"({len(seq)} steps, mode={strat.get('mode', 'manual')})"
            )

    specs = store.list_specs()
    spec_id = scope.get("spec_id")
    if specs:
        parts.append("\n## Project specs")
        for spec in specs[:4]:
            if spec_id and spec["id"] != spec_id:
                continue
            parts.append(f"- [{spec['id']}] {spec.get('title', 'Untitled')}: {_short(spec.get('text', ''), 200)}")
            analysis = spec.get("analysis") or {}
            ranked = sorted(
                analysis.values(),
                key=lambda r: -(r.get("spec_score") or 0),
            )[:5]
            for row in ranked:
                parts.append(
                    f"  · {row.get('title', 'Paper')} — {row.get('relevance', '')}: "
                    f"{_short(row.get('spec_why', ''), 160)}"
                )

    # Papers most related to the user's question (or a small default sample).
    candidates: list[tuple[int, str, dict]] = []
    for proj in usable:
        for item in proj.get("items") or []:
            score = _score_paper(item, query_tokens)
            candidates.append((score, proj["key"], item))
    candidates.sort(key=lambda row: (-row[0], row[2].get("title", "").lower()))
    limit = 20 if query_tokens else 12
    chosen = candidates[:limit]
    if chosen:
        parts.append("\n## Papers (most relevant to this question)")
        for score, pkey, item in chosen:
            parts.append(f"project={pkey}\n{_paper_line(item, abstract=score > 0)}")

    body = "\n".join(parts)
    return body[:14000]
