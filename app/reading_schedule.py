"""Estimate reading time and day-by-day schedule for reading plans."""
from __future__ import annotations

import math

# Medium academic pace: careful read of dense PDFs (~5 min/page).
MEDIUM_PAGES_PER_HOUR = 12
DEFAULT_PAGES = 9  # typical 8–10 page conference/journal article
HOURS_PER_DAY = 2  # focused reading budget used to spread the plan across days
MIN_MINUTES_PER_PAPER = 25


def estimate_pages(paper: dict) -> float:
    """Heuristic page count when Zotero does not provide one."""
    tags = " ".join(paper.get("tags") or []).lower()
    if any(w in tags for w in ("survey", "review", "tutorial", "overview")):
        return 18.0
    item_type = (paper.get("item_type") or "").lower()
    if item_type in {"thesis", "book", "report"}:
        return 35.0
    if item_type in {"conferencePaper", "proceedingsPaper"}:
        return 8.0

    abstract = (paper.get("abstract") or "").split()
    n = len(abstract)
    if n >= 220:
        return 12.0
    if n <= 70:
        return 7.0
    return float(DEFAULT_PAGES)


def estimate_minutes(paper: dict, *, pages_per_hour: float = MEDIUM_PAGES_PER_HOUR) -> int:
    pages = estimate_pages(paper)
    return max(MIN_MINUTES_PER_PAPER, round(pages / pages_per_hour * 60))


def _paper_lookup(projects: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for proj in projects:
        for item in proj.get("items") or []:
            out[item["key"]] = item
    return out


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes / 60
    if abs(hours - round(hours)) < 0.05:
        return f"{int(round(hours))} h"
    return f"{hours:.1f} h"


def attach_reading_schedule(
    plan: dict,
    projects: list[dict],
    *,
    pages_per_hour: float = MEDIUM_PAGES_PER_HOUR,
    hours_per_day: float = HOURS_PER_DAY,
) -> dict:
    """Add per-step read estimates and a plan-level schedule summary."""
    lookup = _paper_lookup(projects)
    daily_budget = max(30, round(hours_per_day * 60))
    sequence = []
    total_minutes = 0
    day = 1
    minutes_today = 0

    for step in plan.get("sequence") or []:
        row = dict(step)
        paper = lookup.get(row.get("paper_key", ""), {})
        read_minutes = estimate_minutes(paper, pages_per_hour=pages_per_hour)
        est_pages = round(estimate_pages(paper), 1)

        if minutes_today and minutes_today + read_minutes > daily_budget:
            day += 1
            minutes_today = 0
        minutes_today += read_minutes
        total_minutes += read_minutes

        row["read_minutes"] = read_minutes
        row["read_pages_est"] = est_pages
        row["scheduled_day"] = day
        sequence.append(row)

    total_hours = round(total_minutes / 60, 1)
    estimated_days = max(1, math.ceil(total_minutes / daily_budget)) if total_minutes else 0
    summary = (
        f"About {_format_duration(total_minutes)} over {estimated_days} day"
        f"{'' if estimated_days == 1 else 's'} at {hours_per_day:g} h/day "
        f"(medium pace, ~{pages_per_hour:g} pages/h)."
    )

    out = dict(plan)
    out["sequence"] = sequence
    out["schedule"] = {
        "pace": "medium",
        "pages_per_hour": pages_per_hour,
        "hours_per_day": hours_per_day,
        "total_minutes": total_minutes,
        "total_hours": total_hours,
        "estimated_days": estimated_days,
        "summary": summary,
    }
    return out
