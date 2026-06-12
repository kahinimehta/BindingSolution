from app.discovery import build_pubmed_query, discover_for_spec, library_titles


def test_build_pubmed_query_uses_spec_and_categories():
    spec = {"text": "We study hippocampal memory consolidation with calcium imaging in mice."}
    projects = [{
        "key": "A",
        "category": {"keywords": ["hippocampus", "memory", "calcium"]},
        "items": [],
    }]
    q = build_pubmed_query(spec["text"], projects)
    assert "hippocampal" in q or "memory" in q
    assert "AND" in q


def test_discover_for_spec_excludes_library_titles():
    spec = {"text": "fairness in machine learning recommender systems"}
    projects = [{
        "key": "A",
        "name": "Fairness",
        "items": [{"key": "P1", "title": "Auditing Recommender Systems for Demographic Skew"}],
    }]
    hits = discover_for_spec(spec, projects, use_mock=True)
    titles = {h["title"].lower() for h in hits}
    assert "auditing recommender systems for demographic skew" not in titles
    assert hits
    assert hits[0].get("url")
