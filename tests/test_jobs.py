def test_list_jobs_empty(client):
    data = client.get("/api/jobs").json()
    assert data["jobs"] == []


def test_list_jobs_includes_sync_and_active_filter(client):
    start = client.post("/api/library/sync", json={"source": "demo"}).json()
    assert "job_id" in start

    listed = client.get("/api/jobs").json()["jobs"]
    assert any(j["id"] == start["job_id"] for j in listed)

    from tests.conftest import run_job

    run_job(client, start)
    job = client.get(f"/api/jobs/{start['job_id']}").json()
    assert job["status"] == "done"

    active = client.get("/api/jobs", params={"active": True}).json()["jobs"]
    assert all(j["status"] in ("queued", "running") for j in active)
    assert not any(j["id"] == start["job_id"] for j in active)
