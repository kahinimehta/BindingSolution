from app.discovery import (
    MAX_DISCOVERIES,
    MIN_RELEVANCE_SCORE,
    build_pubmed_query,
    discover_for_spec,
    library_titles,
    _select_relevant,
)


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
    assert hits[0].get("summary")
    assert hits[0].get("relevance_explanation")


def test_discover_for_spec_caps_at_five():
    spec = {"text": "fairness calibration recommender systems causal inference graphs"}
    hits = discover_for_spec(spec, [], use_mock=True)
    assert len(hits) <= MAX_DISCOVERIES


def test_discover_for_spec_drops_weak_tail():
    spec = {"text": "fairness calibration recommender systems causal inference"}
    hits = discover_for_spec(spec, [], use_mock=True)
    assert all(h["score"] >= MIN_RELEVANCE_SCORE for h in hits)
    assert all(h.get("summary") for h in hits)
    assert len(hits) < 6


def test_select_relevant_respects_score_cutoff():
    terms = ["fairness", "causal", "recommender"]
    hits = [
        {"title": "Strong fairness causal paper", "abstract": "fairness causal recommender", "url": "http://x"},
        {"title": "Weak unrelated note", "abstract": "clinical medicine only", "url": "http://y"},
    ]
    selected = _select_relevant(hits, terms, exclude=set())
    assert len(selected) == 1
    assert "fairness" in selected[0]["title"].lower()


def test_library_titles_normalized():
    projects = {"A": {"items": [{"title": "  Foo   Bar  "}]}}
    assert library_titles(projects) == {"foo bar"}
