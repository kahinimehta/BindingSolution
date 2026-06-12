"""Unit tests for analysis helpers."""
from app.analysis import complete_reading_strategy
from app import mock


def test_complete_reading_strategy_fills_missing_steps():
    projects = [
        {
            "key": "A",
            "name": "Alpha",
            "short_name": "Alpha",
            "items": [
                {"key": "P1", "title": "Paper one"},
                {"key": "P2", "title": "Paper two"},
            ],
        }
    ]
    partial = {
        "title": "Partial plan",
        "goal_restatement": "Learn alpha",
        "approach": "Read one paper.",
        "sequence": [
            {
                "paper_key": "P1",
                "title": "Paper one",
                "project_key": "A",
                "reason": "Start here.",
            }
        ],
        "synthesis_prompts": ["What connects these?"],
    }
    completed = complete_reading_strategy(partial, projects, "Learn alpha")
    keys = [step["paper_key"] for step in completed["sequence"]]
    assert keys == ["P1", "P2"]


def test_complete_reading_strategy_leaves_mock_plan_unchanged():
    projects = [
        {
            "key": "A",
            "name": "Alpha",
            "short_name": "Alpha",
            "items": [{"key": "P1", "title": "Paper one", "tags": ["theory"]}],
        }
    ]
    plan = mock.reading_strategy(projects, "Understand alpha")
    completed = complete_reading_strategy(plan, projects, "Understand alpha")
    assert len(completed["sequence"]) == len(plan["sequence"])
