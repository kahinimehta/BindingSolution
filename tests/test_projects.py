"""Tests for project usability rules."""
from app.projects import UNFILED_KEY, inactive_reason, is_usable_project, usable_projects


def test_usable_project_with_papers():
    proj = {"key": "ABC", "num_items": 3, "items": [{}, {}, {}]}
    assert is_usable_project(proj)
    assert inactive_reason(proj) is None


def test_empty_collection_not_usable():
    proj = {"key": "EMPTY", "num_items": 0, "items": []}
    assert not is_usable_project(proj)
    assert inactive_reason(proj) == "empty"


def test_single_paper_collection_not_usable():
    proj = {"key": "ONE", "num_items": 1, "items": [{}]}
    assert not is_usable_project(proj)
    assert inactive_reason(proj) == "single"


def test_unfiled_not_usable_even_with_papers():
    proj = {"key": UNFILED_KEY, "num_items": 5, "items": [{}] * 5}
    assert not is_usable_project(proj)
    assert inactive_reason(proj) == "unfiled"


def test_usable_projects_filters():
    projects = {
        "a": {"key": "a", "num_items": 2, "items": [{}, {}]},
        "b": {"key": "b", "num_items": 0, "items": []},
        UNFILED_KEY: {"key": UNFILED_KEY, "num_items": 1, "items": [{}]},
    }
    usable = usable_projects(projects)
    assert len(usable) == 1
    assert usable[0]["key"] == "a"
