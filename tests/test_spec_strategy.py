"""Unit tests for spec → reading-plan mapping."""
from app.spec_strategy import attach_spec_mapping, projects_from_spec


def test_projects_from_spec_filters_to_relevant_papers():
    spec = {
        "id": "s1",
        "title": "Aim",
        "analysis": {
            "P1": {"paper_key": "P1", "project_key": "A", "relevance": "core", "score": 80},
            "P2": {"paper_key": "P2", "project_key": "A", "relevance": "supporting", "score": 50},
        },
    }
    projects = {
        "A": {
            "key": "A",
            "name": "Alpha",
            "num_items": 3,
            "items": [
                {"key": "P1", "title": "One"},
                {"key": "P2", "title": "Two"},
                {"key": "P3", "title": "Three"},
            ],
        }
    }
    filtered = projects_from_spec(spec, projects)
    assert len(filtered) == 1
    assert [it["key"] for it in filtered[0]["items"]] == ["P1", "P2"]


def test_attach_spec_mapping_orders_core_first():
    spec = {
        "id": "s1",
        "title": "Grant",
        "analysis": {
            "P1": {
                "paper_key": "P1",
                "relevance": "supporting",
                "score": 40,
                "relevance_explanation": "Supporting hit.",
            },
            "P2": {
                "paper_key": "P2",
                "relevance": "core",
                "score": 90,
                "relevance_explanation": "Core hit.",
            },
        },
    }
    plan = {
        "title": "Plan",
        "sequence": [
            {"paper_key": "P1", "title": "One", "project_key": "A", "reason": "Base."},
            {"paper_key": "P2", "title": "Two", "project_key": "A", "reason": "Base."},
        ],
    }
    mapped = attach_spec_mapping(plan, spec)
    assert mapped["spec_id"] == "s1"
    assert [s["paper_key"] for s in mapped["sequence"]] == ["P2", "P1"]
    assert mapped["sequence"][0]["spec_why"] == "Core hit."
    assert "Core hit." in mapped["sequence"][0]["reason"]
