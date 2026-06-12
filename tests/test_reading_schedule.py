from app.reading_schedule import (
    MEDIUM_PAGES_PER_HOUR,
    attach_reading_schedule,
    estimate_minutes,
    estimate_pages,
)


def test_estimate_pages_uses_tags_and_abstract():
    survey = {"tags": ["survey", "GNN"], "abstract": "x " * 50}
    assert estimate_pages(survey) == 18.0
    short = {"tags": [], "abstract": "brief note", "item_type": "journalArticle"}
    assert estimate_pages(short) == 7.0


def test_attach_reading_schedule_adds_steps_and_summary():
    projects = [
        {
            "key": "A",
            "name": "Alpha",
            "items": [
                {"key": "P1", "title": "One", "tags": ["theory"], "abstract": "word " * 120},
                {"key": "P2", "title": "Two", "tags": [], "abstract": "word " * 120},
            ],
        }
    ]
    plan = {
        "title": "Plan",
        "sequence": [
            {"paper_key": "P1", "title": "One", "project_key": "A", "reason": "First"},
            {"paper_key": "P2", "title": "Two", "project_key": "A", "reason": "Second"},
        ],
    }
    out = attach_reading_schedule(plan, projects, hours_per_day=2)
    assert out["schedule"]["pace"] == "medium"
    assert out["schedule"]["pages_per_hour"] == MEDIUM_PAGES_PER_HOUR
    assert out["schedule"]["total_minutes"] == sum(s["read_minutes"] for s in out["sequence"])
    assert all("scheduled_day" in s and "read_minutes" in s for s in out["sequence"])
    assert "pages/h" in out["schedule"]["summary"]


def test_estimate_minutes_respects_floor():
    paper = {"tags": [], "abstract": "", "item_type": "conferencePaper"}
    assert estimate_minutes(paper) >= 25
