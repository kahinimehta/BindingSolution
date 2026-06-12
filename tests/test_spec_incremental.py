from unittest.mock import patch

from app import mock as mock_llm
from tests.conftest import run_job


def _load_demo(client):
    run_job(client, client.post("/api/library/sync", json={"source": "demo"}).json())


def test_spec_rescreen_only_new_papers(client):
    _load_demo(client)
    spec = client.post(
        "/api/specs",
        data={
            "text": "We study fairness and calibration in recommender systems using causal inference and graphs.",
            "title": "Incremental spec",
        },
    ).json()

    calls = {"n": 0}
    real = mock_llm.assess_paper

    def counting_assess(spec_text, paper):
        calls["n"] += 1
        return real(spec_text, paper)

    with patch.object(mock_llm, "assess_paper", side_effect=counting_assess):
        first = run_job(client, client.post(f"/api/specs/{spec['id']}/analyze", json={}).json())
        first_calls = calls["n"]
        assert first_calls > 0

        second = run_job(client, client.post(f"/api/specs/{spec['id']}/analyze", json={}).json())
        assert calls["n"] == first_calls
        assert second["screened"] == 0
        assert second["skipped"] == first_calls

        full = client.get(f"/api/specs/{spec['id']}").json()
        assert len(full.get("screened_keys") or []) == first_calls
