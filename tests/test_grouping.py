from app.grouping import complete_paper_groups, heuristic_paper_groups, norm_title


def _projects():
    return [
        {
            "key": "A",
            "name": "Fairness",
            "items": [
                {"key": "P1", "title": "Auditing Recommender Systems", "tags": ["fairness", "audit"]},
                {"key": "P2", "title": "Counterfactual Fairness", "tags": ["fairness", "causal"]},
            ],
        },
        {
            "key": "B",
            "name": "Causal",
            "items": [
                {"key": "P3", "title": "Auditing Recommender Systems", "tags": ["fairness", "audit"]},
                {"key": "P4", "title": "IV Methods", "tags": ["causal", "inference"]},
            ],
        },
    ]


def test_norm_title_collapses_whitespace():
    assert norm_title("  Foo   Bar ") == "foo bar"


def test_heuristic_flags_duplicate_titles():
    result = heuristic_paper_groups(_projects())
    drop_keys = {d["paper_key"] for d in result["drops"]}
    assert "P3" in drop_keys or "P1" in drop_keys
    assert any(d["drop_kind"] == "duplicate" for d in result["drops"])


def test_groups_do_not_duplicate_papers():
    result = heuristic_paper_groups(_projects())
    seen: set[str] = set()
    for grp in result["groups"]:
        for key in grp["paper_keys"]:
            assert key not in seen
            seen.add(key)
        assert grp["papers"]
        assert len(grp["papers"]) == len(grp["paper_keys"])


def test_complete_paper_groups_enriches_papers():
    projects = _projects()
    raw = {
        "overview": "Test overview.",
        "groups": [{"name": "Set", "paper_keys": ["P2", "P4"], "project_keys": ["A", "B"], "rationale": "Shared methods."}],
        "drops": [],
    }
    out = complete_paper_groups(raw, projects)
    assert out["groups"][0]["papers"][0]["title"] == "Counterfactual Fairness"
    assert out["groups"][0]["num_papers"] == 2
    assert out["stats"]["total_papers"] == 4


def test_complete_paper_groups_lists_ungrouped():
    projects = _projects()
    raw = {
        "overview": "",
        "groups": [{"name": "Set", "paper_keys": ["P2"], "project_keys": ["A"], "rationale": "One cluster."}],
        "drops": [],
    }
    out = complete_paper_groups(raw, projects)
    ungrouped_keys = {p["paper_key"] for p in out["ungrouped"]}
    assert "P4" in ungrouped_keys
    assert out["stats"]["num_ungrouped"] == len(out["ungrouped"])
    assert out["stats"]["papers_grouped"] + out["stats"]["num_ungrouped"] + out["stats"]["num_drops"] <= out["stats"]["total_papers"]
