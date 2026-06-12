from app.projects import UNFILED_KEY

from app.grouping import (
    append_single_paper_collections,
    complete_paper_groups,
    enrich_group_summaries,
    finalize_shelf_coverage,
    heuristic_paper_groups,
    norm_title,
    synthesize_group_summary,
)


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


def test_complete_paper_groups_preserves_summary():
    projects = _projects()
    raw = {
        "overview": "Test overview.",
        "groups": [{
            "name": "Set",
            "paper_keys": ["P2"],
            "project_keys": ["A"],
            "summary": "Shared fairness theme. Methods overlap. Read together for audit patterns.",
        }],
        "drops": [],
    }
    out = complete_paper_groups(raw, projects)
    assert "fairness theme" in out["groups"][0]["summary"]
    assert out["groups"][0]["summary"] == out["groups"][0]["rationale"]


def test_heuristic_groups_include_multi_sentence_summary():
    result = heuristic_paper_groups(_projects())
    for grp in result["groups"]:
        assert grp.get("summary")
        assert len(grp["summary"].split(".")) >= 2


def test_synthesize_group_summary_mentions_themes():
    projects = _projects()
    index = {it["key"]: it for p in projects for it in p["items"]}
    # build proper index via complete
    from app.grouping import _paper_index
    idx = _paper_index(projects)
    text = synthesize_group_summary("Fairness set", ["P1", "P2"], idx)
    assert "2 papers" in text
    assert "fairness" in text.lower() or "Auditing" in text


def test_complete_paper_groups_synthesizes_missing_summary():
    projects = _projects()
    raw = {
        "overview": "",
        "groups": [{"name": "Methods", "paper_keys": ["P2", "P4"], "project_keys": ["A", "B"]}],
        "drops": [],
    }
    out = complete_paper_groups(raw, projects)
    assert out["groups"][0]["summary"]
    assert len(out["groups"][0]["summary"].split(".")) >= 2


def test_enrich_group_summaries_repairs_stored_rows():
    projects = _projects()
    stored = complete_paper_groups(
        {"overview": "ok", "groups": [{"name": "Set", "paper_keys": ["P2"], "project_keys": ["A"], "summary": "x"}], "drops": []},
        projects,
    )
    stored["groups"][0]["summary"] = ""
    out = enrich_group_summaries(stored, projects)
    assert out["groups"][0]["summary"]
    assert len(out["groups"][0]["summary"]) > 40


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
    assert (
        out["stats"]["papers_grouped"]
        + out["stats"]["num_ungrouped"]
        + out["stats"]["num_drops"]
        == out["stats"]["total_papers"]
    )


def test_append_single_paper_collections():
    projects = _projects()
    all_projects = {
        **{p["key"]: p for p in projects},
        "S": {
            "key": "S",
            "name": "Lone folder",
            "items": [{"key": "LONE", "title": "Only Paper"}],
        },
    }
    raw = complete_paper_groups(
        {"overview": "", "groups": [], "drops": []},
        projects,
    )
    out = append_single_paper_collections(raw, all_projects)
    keys = {p["paper_key"] for p in out["ungrouped"]}
    assert "LONE" in keys
    assert out["stats"]["num_single_collection"] == 1
    assert out["stats"]["unique_papers"] == out["stats"]["total_papers"] + 1
    assert out["stats"]["papers_accounted"] == out["stats"]["unique_papers"]


def test_finalize_shelf_coverage_includes_unfiled():
    projects = _projects()
    all_projects = {
        **{p["key"]: p for p in projects},
        UNFILED_KEY: {
            "key": UNFILED_KEY,
            "name": "Library (unfiled)",
            "items": [{"key": "UF1", "title": "Unfiled Note"}],
        },
    }
    raw = complete_paper_groups(
        {"overview": "", "groups": [], "drops": []},
        projects,
    )
    out = finalize_shelf_coverage(raw, all_projects)
    keys = {p["paper_key"] for p in out["ungrouped"]}
    assert "UF1" in keys
    assert out["stats"]["num_unfiled"] == 1
    assert out["stats"]["papers_accounted"] == out["stats"]["unique_papers"]


def test_finalize_shelf_accounts_for_every_paper():
    out = finalize_shelf_coverage(heuristic_paper_groups(_projects()), _projects())
    stats = out["stats"]
    assert stats["papers_grouped"] + stats["num_ungrouped"] + stats["num_drops"] == stats["unique_papers"]


def test_finalize_tracks_duplicate_filings():
    shared = {"key": "P1", "title": "Shared"}
    projects = {
        "a": {"key": "a", "name": "A", "items": [shared, {"key": "P2", "title": "B"}]},
        "b": {"key": "b", "name": "B", "items": [shared, {"key": "P3", "title": "C"}]},
    }
    raw = complete_paper_groups({"overview": "", "groups": [], "drops": []}, list(projects.values()))
    out = finalize_shelf_coverage(raw, projects)
    assert out["stats"]["collection_entries"] == 4
    assert out["stats"]["unique_papers"] == 3
    assert out["stats"]["duplicate_filings"] == 1
    assert out["stats"]["papers_accounted"] == 3
