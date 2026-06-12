"""Deterministic, offline stand-ins for the Claude analyses.

Active when no ANTHROPIC_API_KEY is set or MOCK_LLM=true. The output shape
matches `schemas.py` exactly and is derived from the real input (tags,
titles) so demo mode and the test-suite look and behave like the real
thing — just without the insight a model would add.
"""
from __future__ import annotations

import re
from collections import Counter

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "via",
    "under", "over", "from", "into", "using", "toward", "towards", "as", "at",
    "by", "is", "are", "we", "our", "this", "that", "these", "those", "be",
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (text or "").lower()) if w not in _STOP]


def _top_tags(items: list[dict], n: int) -> list[str]:
    counter: Counter[str] = Counter()
    for it in items:
        for tag in it.get("tags", []):
            counter[tag] += 1
        counter.update(_tokens(it.get("title", "")))
    return [tag for tag, _ in counter.most_common(n)]


def categorize_project(project: dict) -> dict:
    items = project["items"]
    tags = _top_tags(items, 8)
    name = project.get("short_name") or project["name"]
    maturity = "established" if len(items) >= 5 else "developing" if len(items) >= 3 else "emerging"
    return {
        "discipline": tags[0].title() if tags else "Research",
        "category": name,
        "summary": (
            f"A collection of {len(items)} works centered on {name.lower()}. "
            f"Recurring topics include {', '.join(tags[:3]) or 'several themes'}."
        ),
        "themes": tags[:6] or [name],
        "methods": [t for t in tags if t in {
            "message passing", "attention", "sampling", "auditing", "calibration",
            "doubly robust", "instrumental variables", "counterfactual", "causal",
        }][:5] or tags[3:6],
        "keywords": tags[:8] or [name.lower()],
        "maturity": maturity,
        "_mock": True,
    }


def find_connections(projects: list[dict]) -> dict:
    # Build a tag -> {project_keys} index, then surface tags shared by >=2 projects.
    tag_index: dict[str, set[str]] = {}
    for proj in projects:
        seen = set()
        for it in proj["items"]:
            for tag in it.get("tags", []):
                seen.add(tag)
            seen.update(_tokens(it.get("title", "")))
        for tag in seen:
            tag_index.setdefault(tag, set()).add(proj["key"])

    shared = sorted(
        ((tag, keys) for tag, keys in tag_index.items() if len(keys) >= 2),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )
    threads = []
    for tag, keys in shared[:8]:
        threads.append({
            "label": tag,
            "kind": "method" if " " in tag else "theme",
            "project_keys": sorted(keys),
            "explanation": f"\"{tag}\" appears across {len(keys)} projects.",
            "strength": "strong" if len(keys) >= 3 else "moderate",
        })

    # Cluster = projects that share the most-connected thread.
    clusters = []
    suggested: list[str] = []
    if threads:
        top = threads[0]
        clusters.append({
            "name": f"{top['label'].title()} cluster",
            "project_keys": top["project_keys"],
            "rationale": (
                f"These projects all engage with {top['label']}, so reading them "
                "together highlights shared methods and transferable ideas."
            ),
        })
        suggested = top["project_keys"]

    names = {p["key"]: p["name"] for p in projects}
    return {
        "overview": (
            f"This library spans {len(projects)} projects "
            f"({', '.join(names.values())}). "
            f"{len(threads)} cross-cutting threads link them."
        ),
        "shared_threads": threads,
        "clusters": clusters,
        "suggested_combination": suggested or [p["key"] for p in projects[:2]],
        "_mock": True,
    }


def reading_strategy(projects: list[dict], goal: str) -> dict:
    # Foundational-first: older papers and 'theory'/'survey' tagged items lead.
    flat = []
    for proj in projects:
        for it in proj["items"]:
            flat.append((proj["key"], it))

    def sort_key(entry):
        _, it = entry
        tags = " ".join(it.get("tags", [])).lower()
        foundational = any(w in tags for w in ("theory", "survey", "foundation", "impossibility"))
        return (0 if foundational else 1, it.get("year") or "9999", it.get("title", ""))

    flat.sort(key=sort_key)
    sequence = [
        {
            "paper_key": it["key"],
            "title": it["title"],
            "project_key": pkey,
            "reason": (
                "Foundational — read early to ground later work."
                if i < max(1, len(flat) // 3)
                else "Builds on the foundational reading above."
            ),
        }
        for i, (pkey, it) in enumerate(flat)
    ]
    return {
        "title": "Reading plan: " + " + ".join(p["short_name"] or p["name"] for p in projects),
        "goal_restatement": goal.strip() or "Understand how these projects connect.",
        "approach": (
            "Start with foundational and theoretical papers, then move outward to "
            "applied and method-specific work, finishing with the most recent results. "
            "Papers sharing tags are grouped so connections stay fresh."
        ),
        "sequence": sequence,
        "synthesis_prompts": [
            "What assumptions do these papers share, and where do they diverge?",
            "Which methods recur, and could one project's method address another's open problem?",
            "What is the strongest combined claim these papers could support together?",
        ],
        "_mock": True,
    }


_IRRELEVANT_PHRASES = (
    "lorem ipsum",
    "shopping list",
    "grocery list",
    "buy milk",
    "happy birthday",
    "dear diary",
    "invoice #",
    "rent payment",
    "to-do list",
    "todo list",
)

_SPEC_SIGNALS = {
    "research", "project", "study", "objectives", "objective", "hypothesis",
    "methods", "method", "methodology", "grant", "proposal", "literature",
    "investigate", "investigating", "examines", "examining", "aims", "aim",
    "goal", "goals", "questions", "analysis", "review", "papers", "paper",
    "thesis", "dissertation", "experiment", "findings", "contribution",
    "fairness", "causal", "inference", "calibration", "recommender",
    "develop", "design", "evaluate", "understanding", "explore", "exploring",
}

_PAPER_SIGNALS = (
    "in this paper",
    "we present",
    "we propose",
    "our results",
    "related work",
    "we show that",
    "figure 1",
    "table 1",
    "references",
    "et al.",
    "et al ",
)


def validate_spec(text: str) -> dict:
    lower = (text or "").lower()
    tokens = set(_tokens(text))

    for phrase in _IRRELEVANT_PHRASES:
        if phrase in lower:
            return {
                "is_project_spec": False,
                "detected_kind": "unrelated",
                "message": (
                    "This doesn't look like a project specification — it reads like "
                    "everyday notes or filler text. Upload a grant aim, proposal summary, "
                    "or short description of your research project instead."
                ),
                "_mock": True,
            }

    paper_hits = sum(1 for phrase in _PAPER_SIGNALS if phrase in lower)
    if paper_hits >= 3 or (paper_hits >= 2 and "abstract" in lower):
        return {
            "is_project_spec": False,
            "detected_kind": "academic_paper",
            "message": (
                "This looks like a published paper, not your own project brief. "
                "Paste or upload a grant aim, proposal, or project description "
                "so we can score which library papers matter for your work."
            ),
            "_mock": True,
        }

    personal_phrases = (
        "meeting notes",
        "action items",
        "please find attached",
        "dear ",
        "sincerely",
        "resume",
        "curriculum vitae",
    )
    if any(phrase in lower for phrase in personal_phrases):
        return {
            "is_project_spec": False,
            "detected_kind": "personal_document",
            "message": (
                "This looks like a personal or administrative document, not a research "
                "project spec. Upload a grant aim, proposal, or short description of "
                "what you are trying to investigate."
            ),
            "_mock": True,
        }

    spec_hits = len(tokens & _SPEC_SIGNALS)
    if spec_hits >= 2 or (spec_hits >= 1 and len(text) >= 60):
        return {
            "is_project_spec": True,
            "detected_kind": "project_spec",
            "message": "Looks like a project specification.",
            "_mock": True,
        }

    if spec_hits == 0:
        return {
            "is_project_spec": False,
            "detected_kind": "unrelated",
            "message": (
                "This doesn't look like a project specification. Describe your research "
                "goals, questions, or methods — for example a grant aim or one-paragraph "
                "proposal — and try again."
            ),
            "_mock": True,
        }

    return {
        "is_project_spec": True,
        "detected_kind": "project_spec",
        "message": "Looks like a project specification.",
        "_mock": True,
    }


def assess_paper(spec_text: str, paper: dict) -> dict:
    spec_tokens = set(_tokens(spec_text))
    paper_tokens = set(_tokens(paper.get("title", "")) + _tokens(paper.get("abstract", "")))
    paper_tokens.update(t.lower() for t in paper.get("tags", []))
    overlap = spec_tokens & paper_tokens
    score = max(0, min(100, len(overlap) * 12))
    if score >= 60:
        relevance = "core"
    elif score >= 35:
        relevance = "supporting"
    elif score >= 15:
        relevance = "tangential"
    else:
        relevance = "not_relevant"
    shared = sorted(overlap)[:3]
    return {
        "paper_key": paper["key"],
        "relevance": relevance,
        "score": score,
        "summary": (
            (paper.get("abstract") or paper["title"])[:300]
        ),
        "relevance_explanation": (
            f"Shares concepts ({', '.join(shared)}) with the spec."
            if shared
            else "Little overlap with the spec's stated focus."
        ),
        "use_for": [f"Reference for {t}" for t in shared] or ["Background context"],
        "_mock": True,
    }
