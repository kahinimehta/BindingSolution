from app.spec_analysis import bootstrap_screened_keys, papers_to_screen, prune_analysis


def _paper(key: str, title: str = "Paper") -> dict:
    return {"key": key, "title": title}


def test_papers_to_screen_first_run():
    spec = {"status": "new", "analysis": {}, "screened_keys": []}
    papers = [("p1", _paper("a")), ("p1", _paper("b"))]
    to_screen, screened, skipped = papers_to_screen(spec, papers)
    assert len(to_screen) == 2
    assert skipped == 0
    assert screened == set()


def test_papers_to_screen_incremental():
    spec = {
        "status": "analyzed",
        "analysis": {"a": {"relevance": "core"}},
        "screened_keys": ["a", "b"],
        "num_screened": 2,
    }
    papers = [("p1", _paper("a")), ("p1", _paper("b")), ("p2", _paper("c"))]
    to_screen, screened, skipped = papers_to_screen(spec, papers)
    assert [p["key"] for _, p in to_screen] == ["c"]
    assert skipped == 2
    assert screened == {"a", "b"}


def test_bootstrap_legacy_when_counts_match():
    spec = {"status": "analyzed", "analysis": {"a": {}}, "num_screened": 2}
    papers = [("p1", _paper("a")), ("p1", _paper("b"))]
    screened = bootstrap_screened_keys(spec, papers)
    assert screened == {"a", "b"}


def test_prune_analysis_drops_removed_papers():
    analysis = {"a": {"relevance": "core"}, "gone": {"relevance": "supporting"}}
    pruned = prune_analysis(analysis, {"a"})
    assert set(pruned) == {"a"}
